# SPUDNIG
This repository contains the source code of the SPeeding Up the Detection of Non-iconic and Iconic Gestures (SPUDNIG) toolkit. A working version of the application can be downloaded [here](www.test.com). SPUDNIG is created during my MSc thesis project at the Max Planck Institute Nijmegen. SPUDNIG's purpose is to speed up annotation work of hand gestures in Elan. SPUDNIG takes as input a video file and extracts the gestures and their timing.

SPUDNIG makes use of [OpenPose](https://github.com/CMU-Perceptual-Computing-Lab/openpose) in order to obtain x- and y-coordinates of keypoints in the body and hands. Based on this information gestures and their timing are calculated and a .csv file is created which is importable by [Elan](https://tla.mpi.nl/tools/tla-tools/elan/).

SPUDNIG only accepts .avi files because OpenPose performs optimal when using this format. Other formats cause OpenPose to skip frames which again disrupts the timing of the gestures. [This site](https://www.any-video-converter.com/products/for_video_free/) allows you to convert your videos to .avi files if needed.


Below you can find a screenshot of SPUDNIG ready to analyze a video:
![alt text](https://github.com/jorrip/SPUDNIG/blob/master/Screenshot.png)












