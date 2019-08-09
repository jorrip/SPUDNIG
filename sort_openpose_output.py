# -*- coding: utf-8 -*-
"""
Created on Tue Jun  4 11:11:10 2019

Converts OpenPose output to 3 csv files for the right-, left-hand and body pose.

@author: jorrip
"""
import json
import pandas as pd
import os

def sort_openpose(root):
    '''Converts the OpenPose output to CSV files for the movement analyzer.'''
    hand_left = []
    hand_right = []
    pose = []

    index = 0
    for subdir, dirs, files in os.walk(root):
        for file in files:
            #print(index)
            with open(os.path.join(subdir, file), "r") as read_file:
                data = json.load(read_file)
            hand_left.append(data['people'][0]['hand_left_keypoints_2d'])
            hand_right.append(data['people'][0]['hand_right_keypoints_2d'])
            pose.append(data['people'][0]['pose_keypoints_2d'])
            index = index+1

    pose_csv = pd.DataFrame(pose)
    hand_left_csv = pd.DataFrame(hand_left)
    hand_right_csv = pd.DataFrame(hand_right)

    hand_left_csv.to_csv(root + "\\" + r'hand_left_sample.csv', encoding='utf-8', index=False, header=None)
    hand_right_csv.to_csv(root + "\\" +r'hand_right_sample.csv', encoding='utf-8', index=False, header=None)
    pose_csv.to_csv(root + "\\" + r'sample.csv', encoding='utf-8', index=False, header=None)            
    
