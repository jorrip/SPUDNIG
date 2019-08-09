import tkinter as tk
from tkinter.ttk import Progressbar, Frame
from tkinter import filedialog, messagebox, simpledialog
import cv2
from PIL import Image, ImageTk
import os
import sort_openpose_output, movements
import subprocess
import threading
import time
import tempfile
import shutil
import re


cpu = False
fpsGlobal = -1
threshold = 0.3
goAnalyze = False
threads = []
left = True
right = True


class cd:
    """Context manager for changing the current working directory"""
    def __init__(self, newPath):
        self.newPath = os.path.expanduser(newPath)

    def __enter__(self):
        self.savedPath = os.getcwd()
        os.chdir(self.newPath)

    def __exit__(self, etype, value, traceback):
        os.chdir(self.savedPath)
        

class SettingsGUI:
    '''Small GUI for the settings screen before analyzing.'''
    def __init__(self, master):
        self.master = master
        self.open = True # indicates if the settings screen is open
        self.master.title("Settings")
        master.iconbitmap('spudnig.ico')
        self.completed = False
        self.cancelled = False

        tk.Label(master, text="Frames per second (fps):").grid(row=0)
        tk.Label(master, text="Reliability threshold:").grid(row=1)

        self.e1 = tk.Entry(master)
        self.e1.insert(0,str(fpsGlobal))
        self.e2 = tk.Entry(master)
        self.e2.insert(0,str(0.3))
        
        self.checkLeft = tk.IntVar()
        self.checkRight = tk.IntVar()
        self.c1 = tk.Checkbutton(master, text= "Left hand", variable=self.checkLeft, onvalue= 1, offvalue = 0)
        self.c2 = tk.Checkbutton(master, text= "Right hand", variable=self.checkRight, onvalue= 1, offvalue = 0)
        self.c1.select()
        self.c2.select()

        self.e1.grid(row=0, column=1)
        self.e2.grid(row=1, column=1)
        
        self.c1.grid(row=2,column=0)
        self.c2.grid(row=2,column=1)
        
        self.ok = tk.Button(master, text="OK",command=self.apply)
        self.ok.grid(row=3, column=0)
        
        self.cancel = tk.Button(master, text="Cancel", command=self.cancelSettings)
        self.cancel.grid(row=3, column=1)
        self.master.protocol("WM_DELETE_WINDOW", self.cancelSettings)
        
        # thread closes settings screen when open for too long
        closeSettingsThread = threading.Thread(target=self.shutDown)
        closeSettingsThread.start()
        threads.append(closeSettingsThread)
        
    
    def cancelSettings(self):
        '''Closes the settings screen by clicking cancel button'''
        self.open = False
        self.cancelled = True
        self.master.destroy()


    def apply(self):
        '''Function that is called when OK button in settings screen is clicked.'''
        global threshold
        global fpsGlobal
        global goAnalyze
        global left, right
        
        # check input for reliability settings
        threshold = self.e2.get()
        if not re.search(r"[0]\.[1-9]",threshold):
            self.open = False
            self.cancelled = True
            self.master.destroy()
            tk.messagebox.showerror("Invalid number", "The reliability threshold should be a decimal between 0-1 split by a dot (e.g. 0.3).")
            return
        
        threshold = float(threshold)
        fpsGlobal = int(self.e1.get())
        
        if self.checkLeft.get() is 0:
            left = False
        if self.checkRight.get() is 0:
            right = False
        
        goAnalyze = True
        self.master.destroy()
        self.open = False
        self.completed = True
    
    
    def shutDown(self):
        '''Shuts down settings screen when open for too long.'''
        must_end = time.time() + 600
        while time.time() < must_end:
            if not self.open:
                break
            time.sleep(0.25)
        
        if self.open:
            self.master.destroy()
            messagebox.showerror("Error", "You timed out. Please click Analyze again if you want analyze the video.")
            return
        else: 
            return


class GUI:
    '''GUI for the application.'''
    def __init__(self, master):
        self.master = master
        self.tempDir = tempfile.mkdtemp()
        print(self.tempDir)
        self.master.title("SPUDNIG")
        self.readyForAnalysis = False
        self.workdir = os.getcwd()
        master.iconbitmap('spudnig.ico')
        
        if cpu:
            self.openpose = self.workdir + "\openpose_cpu/bin/OpenPoseDemo.exe" 
        else: 
            self.openpose = self.workdir + "\openpose_gpu/bin/OpenPoseDemo.exe" 
            
        self.data = None
        self.fps = fpsGlobal
        self.finished = False
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.frame = tk.Frame(master)
        self.frame.pack()
    
        self.menu = tk.Menu(self.frame)
        self.file_expand = tk.Menu(self.menu, tearoff=0)
        self.file_expand.add_command(label='New...',command=self.newFile)
        self.file_expand.add_command(label='Open...',command=self.openVideo)
        self.file_expand.add_command(label='Save as...',command=self.saveFile)
        self.file_expand.add_command(label='About',command=self.showAbout)
        self.menu.add_cascade(label='File', menu=self.file_expand)
        self.master.config(menu=self.menu)
        
        
        self.welcome = tk.Label(self.frame, 
                                text="Welcome to SPUDNIG. Select a file to analyze via File -> Open...")
        self.welcome.pack(pady=20)
        
        self.bottomframe = tk.Frame(self.master)
        self.bottomframe.pack(side=tk.BOTTOM)
        
        
        self.analyzeButton = tk.Button(self.bottomframe, text='Analyze',   command=self.analyzeButtonClicked)
        self.analyzeButton.pack(side=tk.BOTTOM,pady=20)
        self.analyzeButton.configure(font=('Sans','13','bold'), background = 'red2')

        self.progress = Progressbar(self.bottomframe, length=200, orient=tk.HORIZONTAL,mode='determinate')
        self.progress['value'] = 0
        self.barLabel = tk.Label(self.bottomframe,text='Analyzing...',font='Bold')
        
        global left, right
        left = True
        right = True
    
    
    def saveFile(self):
        '''Saves the Elan importable file on a location selected by the user.'''
        if self.finished:
            self.saved = False
            self.savefile =  filedialog.asksaveasfilename(initialdir = "/",title = "Save file",filetypes = (("csv files","*.csv"),("all files","*.*")))
            if self.savefile is None:
                return
            else:
                if not self.savefile.endswith(".csv"):
                    self.savefile += ".csv"
                self.data.to_csv(self.savefile,header=False)
                self.saved = True
                # TODO: delete files
                subprocess.run('RMDIR /Q/S ' + self.outputfoler, shell=True)
                subprocess.run('del hand_left_sample.csv', shell=True)
                subprocess.run('del hand_right_sample.csv', shell=True)
                subprocess.run('del sample.csv', shell=True)
        else: 
            tk.messagebox.showerror("No file", "There's nothing to save yet.")
    
    
    def newFile(self):
        '''Opens a new window after new button is clicked.'''
        input = tk.messagebox.askokcancel("Warning", "Opening a new window will close the old one and unsaved data will be lost.")
        if input:
            shutil.rmtree(self.tempDir)
            self.master.destroy()
            
            newWindow = tk.Tk()
            newWindow.geometry('1000x750')
            new_gui = GUI(newWindow)
            newWindow.mainloop()
        
        
    def showAbout(self):
        tk.messagebox.showinfo("About SPUDNIG", "SPeeding Up the Detection of Non-iconic and Iconic Gestures (SPUDNIG) is a toolkit for the"
                               + " automatic detection of hand movements and gestures in video data. \n\nIt is developed by Jordy Ripperda, a MSc"
                               + " student in Artificial Intelligence at the Radboud University in Nijmegen (Netherlands). This toolkit was"
                               + " developed during my thesis project at the Max Planck Institute for Psycholinguistics also in Nijmegen.")
    
    
    def openVideo(self): 
        '''Starts thread for opening video.'''
        self.filename = filedialog.askopenfilename(initialdir = '/', title = 'Select file', filetypes = (("avi files",".avi"),("all files","*.*")))
        if self.filename:
            openVidThread = threading.Thread(target=self.openVideoThread)
            openVidThread.start()
            threads.append(openVidThread)
    
    
    def openVideoThread(self):
        '''Opens the video when open... button is clicked and shows a screenshot of a frame from the video'''
        # read videofile
        cap = cv2.VideoCapture(self.filename)
        self.totalFrames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        global fpsGlobal 
        fpsGlobal = int(cap.get(cv2.CAP_PROP_FPS))
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(self.totalFrames/2))
        ret,frame = cap.read()
        cv2.imwrite(self.tempDir + r"\image.jpg", frame)
        
        # show image
        image = Image.open(self.tempDir + r"\image.jpg")
        resizedImg = image.resize((640, 360), Image.ANTIALIAS)
        picture = ImageTk.PhotoImage(resizedImg)
        self.label = tk.Label(self.frame,image=picture)
        self.label.image = picture
        self.label.pack()
        
        cap.release()
        cv2.destroyAllWindows()
        
        self.readyForAnalysis = True
        self.analyzeButton.configure(background='green2')
        self.welcome.config(text="Start the analysis of the video by clicking the 'Analyze' button." )
            
            
    def startAnalysis(self):
        '''Target function of the thread that waits for the user to finish the settings and start the analysis.'''
        must_end = time.time() + 600
        while time.time() < must_end:
            if goAnalyze is True:
                actualAnalysisThread = threading.Thread(target=self.analysis)
                actualAnalysisThread.start()
                threads.append(actualAnalysisThread)
                break
            time.sleep(0.25)
        if time.time() >= must_end:        
            print('timed out')
        return
    
    
    def showSaveButton(self):
        '''Target function of thread that shows the save button when analysis is finished'''
        must_end = time.time() + self.totalFrames * 2
        while time.time() < must_end:
            if self.finished is True:
                self.saveButton = tk.Button(self.bottomframe, text='Export', command=self.saveFile)
                self.analyzeButton.forget()
                self.saveButton.pack(side=tk.BOTTOM,pady=20)
                self.saveButton.configure(font=('Sans','13','bold'), background = 'deep sky blue')
                self.welcome.config(text="Save the .csv file containing the movements through the 'Export' button or via File -> Save as..." )
                break
            time.sleep(0.25)
        return


    def analyzeButtonClicked(self):
        '''Loads the settings screen before the analysis starts'''
        if not self.readyForAnalysis:
            messagebox.showerror("Error", "Select a video file before you start the analysis.")  
        else: 
            settings = tk.Toplevel(self.master)
            settingsGUI = SettingsGUI(settings)
            analyzeOrNotThread = threading.Thread(target=self.analyzeOrNOt, args=[settingsGUI])
            analyzeOrNotThread.start()
            threads.append(analyzeOrNotThread)
            
    
    def analyzeOrNOt(self, gui):
        '''Checks if settings screen is completed.'''
        must_end = time.time() + 600
        while time.time() < must_end:
            if gui.completed:
                startAnalysisThread = threading.Thread(target=self.startAnalysis)
                startAnalysisThread.start()
                threads.append(startAnalysisThread)
                showSaveButtonThread = threading.Thread(target=self.showSaveButton)
                showSaveButtonThread.start()
                threads.append(showSaveButtonThread)
                break
            if gui.cancelled:
                break
            time.sleep(0.25)
            
    def updateBar(self):
        '''Updates the progress bar.'''
        progress = 0.0
        total = self.totalFrames
        if cpu:
            fpm = 5
        else: 
            fpm = 100
        progressPerSec = (80/((total/fpm)*60))/2
        print(progressPerSec)
        while not self.finished:
            progress += progressPerSec
            self.progress['value'] = progress
            time.sleep(0.5)
            
    
    def analysis(self):
        '''Starts the analysis of the video when analyze button is clicked'''   
        self.fps = fpsGlobal
        
        self.barLabel.pack(side=tk.TOP)
        self.progress.pack(side=tk.TOP)
        
        self.base = os.path.basename(self.filename)
        self.outputfoler = os.path.splitext(self.base)[0]
        updateBarThread = threading.Thread(target=self.updateBar)
        updateBarThread.start()
        threads.append(updateBarThread)
        subprocess.run(['mkdir', self.tempDir + r"/" + self.outputfoler], shell=True)
        if cpu:
            try:
                with cd("openpose_cpu"):
                    subprocess.run(self.openpose + " --video " + self.filename + " -num_gpu -1 --hand --write_json " 
                                       	+ self.tempDir + "/" + self.outputfoler + " --model_pose BODY_25 --net_resolution -1x144 number_people_max 1 --display 0 --render_pose 0",shell=True, stdout=subprocess.PIPE)
            except: 
                print('Something went wrong with OpenPose')
        else: 
            try:
               with cd("openpose_gpu"):
                    subprocess.run(self.openpose + " --video " + self.filename + " -num_gpu -1 --hand --write_json " 
                                       	+ self.tempDir + "/" + self.outputfoler + " --model_pose BODY_25 --net_resolution -1x144 number_people_max 1 --display 0 --render_pose 0",shell=True, stdout=subprocess.PIPE)
            except: 
                print('Something went wrong with OpenPose')
        self.progress['value'] = 75
        sort_openpose_output.sort_openpose(self.tempDir + "\\" + self.outputfoler)
        self.progress['value'] = 85
        self.data = movements.main(self.tempDir + "\\" + self.outputfoler, self.fps, threshold, left, right)

        
        self.progress['value'] = 100
        self.barLabel['text'] = "Finished"
        self.finished = True
        return
    

    def on_close(self):
        close = messagebox.askokcancel("Close", "Would you like to close the program?")
        if close:
            for t in threads:      
                t.join()
            self.master.destroy()  
            shutil.rmtree(self.tempDir)
            
        
def main():
    root = tk.Tk()
    root.geometry('1000x576')
    my_gui = GUI(root)
    root.mainloop()
    

if __name__== "__main__":
    main()





