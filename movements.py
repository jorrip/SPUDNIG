# -*- coding: utf-8 -*-
"""
Created on Tue Jun  4 17:20:50 2019

@author: jorrip
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy
from operator import itemgetter

# The data for the pose, right- and left-hand need to be stored in csv's 
# that can be created with the script sort_openpose_output


def merge_gestures(l1,l2):
    '''Merges 2 gesture dataframes into 1.'''
    if len(l1) != len(l2):
        print("Lists should have same lengths. " + str(len(l1)) + " and " + str(len(l2)) + " do not match.")
        return
    l3 = []
    for x in range(len(l1)):
        if l1[x] + l2[x] > 0:
            l3.append(1)
        else: 
            l3.append(0)
    return l3


def rest(i,data,keypoint):
    '''Determines whether current point is in rest position'''
    x = data.loc[i][keypoint]
    y = data.loc[i][keypoint+1]
    span = 14
    
    start = int(i - span/2)
    if start < 0: 
        start = 0
    end = int(i + span/2)
    if end > data.shape[0]:
        end = data.shape[0]
        
    certainty = 0
    for j in range(start,end):
        if abs(data.loc[j][keypoint] - x) < 10 and abs(data.loc[j][keypoint+1] - y) < 10:
            certainty += 1
            
    if certainty/span >= 0.7:
        return True
    else: 
        return False
    

def frameToTime(i,fps):
    '''Converts the framenumber to hh:mm:ss:ms format'''
    milliseconds_in_hour = 3600000
    milliseconds_in_minute = 60000
    milliseconds_in_second = 1000

    milliseconds = int(i*(1000/fps))

    hours = milliseconds // milliseconds_in_hour
    milliseconds = milliseconds - (hours * milliseconds_in_hour)

    minutes = milliseconds // milliseconds_in_minute
    milliseconds = milliseconds - (minutes * milliseconds_in_minute)

    seconds = milliseconds // milliseconds_in_second
    milliseconds = milliseconds - (seconds * milliseconds_in_second)
    
    return "{0:.0f}:{1:.0f}:{2:.0f}.{3:0>3d}".format(hours,minutes,seconds,milliseconds)
        

    
def get_gestures(data,keypoint,threshold=0.3):
    '''Recognizes gestures that occur in data based on keypoint 'keypoint' and stores outcomes in gestures.'''
    local_gestures = [0]
    rest_x = 0
    rest_y = 0
    keypoint = keypoint*3

    i = 0
    # fill right hand gestures 
    while i < data.shape[0]-1:
        i = i+1
        gesture = 0
        current = data.loc[i]
        prev = data.loc[i-1]
        returned = False
        backToRest = -1
        
        
        # if certainty (of openpose) is too low there is no gesture
        if current[keypoint+2] < threshold:
            local_gestures.append(gesture)
        
        else:
            # update rest position
            if rest(i,data,keypoint):
                rest_x = current[keypoint]
                rest_y = current[keypoint+1]
                gesture = 0

            # if hand coordinates are different from previous frame
            elif abs(current[keypoint] - rest_x) > 5 or abs(current[keypoint+1] - rest_y) > 5:
                # check if it's actual movement or just a few frames
                certainty = 0
                for x in range(i+1,min(i+6,data.shape[0])):
                    if abs(data.loc[x][keypoint] - rest_x) > 5 or abs(data.loc[x][keypoint+1] - rest_y) > 5:
                        certainty += 1
                # if there is no movement
                if certainty/5 < 0.5:
                    gesture = 0
                # if there is indeed movement
                else:
                    # TODO: check whether hands return to rest position in future: if so, there is a gesture from current i until it reaches rest point again
                    for t in range(i+1, min(i+300,data.shape[0])):
                        # if hand has returned to rest position in next 10 seconds
                        if isStill(data,t,keypoint):
                            gesture = 1
                            returned = True
                            backToRest = t
                            rest_x = data.loc[t][keypoint]
                            rest_y = data.loc[t][keypoint+1]
                            break
                            

                    # if hands did not return to previous rest position, check if they returned to new restposition
                    if not returned:
                        for t in range(i+1, min(i+300,data.shape[0])):
                            if rest(t,data,keypoint):
                                gesture = 1
                                returned = True
                                backToRest = t
                                rest_x = data.loc[backToRest][keypoint]
                                rest_y = data.loc[backToRest][keypoint+1]
                                break;

            if returned:
                for k in range(i,backToRest+1):
                    local_gestures.append(gesture)
                i = backToRest
            else:
                local_gestures.append(gesture)
            
    return local_gestures


def post_process(data):
    '''Post processing of the gestures. Gestures smaller than 4 frames are removed.
    Consequetive gestures with less than 4 frames between them are merged together.'''
    newdata = data.copy()
    idx = 0
    cutoff = 4
    # merge consequetive gestures with fewer than 4 frames between them
    while idx < len(newdata)-1:
        if newdata[idx] == 1 and newdata[idx+1] == 0:
            try:
                nextone = next((j,val) for j, val in enumerate(newdata[idx+1:]) if val == 1)[0]
            except StopIteration:
                break
            if nextone <= cutoff:
                for j in range(idx+1,idx+nextone+1):
                    newdata[j] = 1
            idx = idx + nextone + 1
        else:
            idx = idx + 1
            
    idx = 0
    # remove gestures that are shorter than 4 frames
    while idx < len(newdata)-1:
        if newdata[idx] == 1:
            try:
                nextone = next((j,val) for j, val in enumerate(newdata[idx:]) if val == 0)[0]
            except StopIteration:
                break
            if nextone <= cutoff:
                for j in range(idx,idx+nextone+1):
                    newdata[j] = 0
            idx = idx + nextone + 1

        else:
            idx = idx + 1
       
    return newdata


def isStill(data,idx,keypoint):
    '''Returns true if the current idx point is resting'''
    count = 0
    current = data.loc[idx]
    for x in range(min(idx+1,data.shape[0]), min(idx+21,data.shape[0])):
        if abs(current[keypoint] - data.loc[x][keypoint]) < 8 and abs(current[keypoint+1] - data.loc[x][keypoint+1]) < 8:
            count += 1
    if count/20 > 0.7:
        return True
    else:
        return False


def most_certain_keypoints(data):
    '''Returns one keypoint from the fingers with the hihghest certainty and one keypoints from the hand palm
    with the highest certainty.'''
    fingers = [2,3,4,6,7,8,10,11,12,14,15,16,18,19,20]
    certainty_keypoints = []
    c = 2
    while c < data.shape[1]:
        certainty_keypoints.append((c,sum(data[c])/len(data[c])))
        c = c + 3
    certainty_keypoints.sort(key=itemgetter(1), reverse=True)
    best = []
    i = 0
    for i in range(len(certainty_keypoints)):
        best.append(int(((certainty_keypoints[i][0]+1)/3)-1))
    
    return [next(x for x in best if x in fingers),
            next(x for x in best if x not in fingers)]
    

def elan_writer(list_of_gestures,fps):
    '''Converts a list of zeros and ones for each frame into a csv that can be imported into Elan.'''
    elan = pd.DataFrame(columns=['Tier','Begin','End','Annotation'])
    idx = 0
    while idx < len(list_of_gestures)-1:
        val = list_of_gestures[idx]     
        if val == 1:
            begin = frameToTime(idx,fps) # there's a 15 frame difference between original/openpose output video
            end = ''
            for idx2, val2 in enumerate(list_of_gestures[idx+1:]):
                if val2 == 0:
                    end = frameToTime(idx+idx2,fps)
                    break
            elan = elan.append({'Tier':'Movements', 'Begin':begin, 'End':end, 'Annotation':'movement'},ignore_index=True)
            idx = idx + idx2 + 1
        else:
            idx += 1
    return elan
    
    
def main(root, fps, threshold, left, right):
    pose = pd.read_csv(root + "/" + r"sample.csv", header=None)
    left_hand = pd.read_csv(root + "/" + r"hand_left_sample.csv", header=None)
    right_hand = pd.read_csv(root + "/" + r"hand_right_sample.csv", header=None)
    
    if left and not right:
        pose_left = get_gestures(pose,7, threshold)
        left1 = get_gestures(left_hand,8, threshold)
        left2 = get_gestures(pose,6, threshold)
        thumb2 = get_gestures(left_hand,4, threshold)
        
        merge1 = merge_gestures(pose_left,left1)
        merge2 = merge_gestures(merge1,left2)
        final = merge_gestures(merge2,thumb2)
        
        processed = post_process(final)
        elan = elan_writer(processed,fps)
        return elan
        
    
    if right and not left:
        pose_right = get_gestures(pose,4, threshold)
        right1 = get_gestures(right_hand,8, threshold)
        right2 = get_gestures(pose,3, threshold)
        thumb1 = get_gestures(right_hand,4, threshold)
        
        merge1 = merge_gestures(pose_right,right1)
        merge2 = merge_gestures(merge1,right2)
        final = merge_gestures(merge2,thumb1)
        
        processed = post_process(final)
        elan = elan_writer(processed,fps)
        return elan
        
    
    if left and right:
        pose_right = get_gestures(pose,4, threshold)
        pose_left = get_gestures(pose,7, threshold)
        
        right1 = get_gestures(right_hand,8, threshold)
        left2 = get_gestures(pose,6, threshold)
        thumb1 = get_gestures(right_hand,4, threshold)
        
        left1 = get_gestures(left_hand,8, threshold)
        right2 = get_gestures(pose,3, threshold)
        thumb2 = get_gestures(left_hand,4, threshold)
        
        merge1 = merge_gestures(pose_right,pose_left)
        merge2 = merge_gestures(merge1,thumb1)
        merge3 = merge_gestures(merge2,thumb2)
        merge4 = merge_gestures(merge3,right1)
        merge5 = merge_gestures(merge4,right2)
        merge6 = merge_gestures(merge5,left2)
        final = merge_gestures(merge6,left1)
        
        processed = post_process(final)
        elan = elan_writer(processed,fps)
        return elan
    
    
    