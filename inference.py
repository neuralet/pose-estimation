import cv2
import numpy as np   
from openpifpaf_tensorrt import PoseEstimator 
from decoder import CifCafDecoder
from utils.fps_calculator import convert_infr_time_to_fps

import random
import logging
import sys
import configparser
import time 

def inference_image(img_orig, pose_estimator, model_input_size,config):
    img_input = cv2.cvtColor(img_orig, cv2.COLOR_BGR2RGB)
    img_normalized = np.zeros(img_orig.shape)
    img_normalized = cv2.normalize(img_input,  img_normalized, 0, 255, cv2.NORM_MINMAX)
    t_begin = time.perf_counter()
    heads = pose_estimator.inference(img_normalized)
    inference_time = time.perf_counter() - t_begin
    
    t_begin = time.perf_counter()
    decoder = CifCafDecoder()
    fields = heads
    predictions = decoder.decode(fields)
    decoder_time = time.perf_counter() - t_begin
    fps = convert_infr_time_to_fps(inference_time+decoder_time)
    print(f'inference time is {inference_time} and decoder time is :{decoder_time} and fps:{fps}') 

    img_vis = cv2.resize(img_orig, model_input_size)

    for i, pred_object in enumerate(predictions):

        pred = pred_object.data
        pred_visible = pred[pred[:, 2] > 0]
        xs = pred_visible[:, 0]
        ys = pred_visible[:, 1]
        color = (random.randint(60, 200), random.randint(0, 255), random.randint(0, 255))
        for x,y in zip(xs,ys):
             cv2.circle(img_vis,(x, y), 2, color, -1)
        decode_order=[(a,b) for (a,b,c,d) in pred_object.decoding_order]
        for index, (a,b) in enumerate(decode_order):
            if (a+1,b+1) in pred_object.skeleton or (b+1,a+1) in pred_object.skeleton:
                x1,y1,_ = pred_object.decoding_order[index][2]   
                x2,y2,_ = pred_object.decoding_order[index][3]
            else:
                continue
            cv2.line(img_vis, ( x1, y1), ( x2, y2), color, 1)
    return img_vis

 
def main():
    config = configparser.ConfigParser()
    config.read(sys.argv[1])
    logging.basicConfig(level=logging.DEBUG)
    w,h = [int (i) for i in config['PoseEstimator']['InputSize'].split(',')] 
    model_input_size=(w,h) 
    pose_estimator = PoseEstimator(config)
    input_path=config['App']['InputPath']
    output_path=config['App']['OutputPath']
    if config['App']['ProcessVideo'] == 'yes':
        input_cap = cv2.VideoCapture(input_path)
        output_cap = cv2.VideoWriter(output_path,cv2.VideoWriter_fourcc('M','J','P','G'), 10, model_input_size)
        if (input_cap.isOpened()):
            print('opened video ', input_path)
        else:
            print('failed to load video ', input_path)
            return

        while input_cap.isOpened():
            _, img_orig = input_cap.read()
            if np.shape(img_orig) != ():
                output_img = inference_image(img_orig, pose_estimator, model_input_size, config)
                output_cap.write(output_img)
            else:
               break 
    elif config['App']['ProcessVideo'] == 'no':
        img_orig = cv2.imread(input_path)
        h,w,_ = img_orig.shape
        orig_size = (w,h)
        if np.shape(img_orig) != ():
            output_img = inference_image(img_orig, pose_estimator, model_input_size, config)
            output_img = cv2.resize(output_img, orig_size)
            cv2.imwrite(output_path,output_img)
            print('Output image is saved!')
        else:
            print('image not found', input_path)


if __name__ == "__main__":
    main()
