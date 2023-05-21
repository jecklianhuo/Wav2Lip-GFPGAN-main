import os
import random
import cv2
from tqdm import tqdm
from os import path


def run_command(cmd):
    print(cmd)
    return_code = os.system(cmd)

    # 检查返回代码
    return return_code


def process_video_with_wav2lip(input_video_path, input_audio_path, output_path):
    wav2lip_cmd = f"D:/AI/Wav2Lip-GFPGAN-main/venv/Scripts/python.exe {wav2lipFolderName}/inference.py --checkpoint_path {wav2lipFolderName}/checkpoints/wav2lip.pth --face {input_video_path} --audio {input_audio_path} --outfile {output_path} --resize_factor 2 --fps 60  --face_det_batch_size 8 --wav2lip_batch_size 128"
    result = run_command(wav2lip_cmd)
    if result != 0:
        print("An error occurred while running Wav2Lip")
    return result


def process_images_with_gfpgan(input_folder, output_folder):
    gfpgan_cmd = f"D:/AI/Wav2Lip-GFPGAN-main/venv/Scripts/python.exe {gfpganPath}/inference_gfpgan.py -i {input_folder} -o {output_folder} -v 1.4 -s 2 --only_center_face --bg_upsampler None"
    result = run_command(gfpgan_cmd)
    if result != 0:
        print("An error occurred while running GFPGAN")
    return result


def extract_frames_from_video(video_path, output_folder):
    vidcap = cv2.VideoCapture(video_path)
    number_of_frames = int(vidcap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = vidcap.get(cv2.CAP_PROP_FPS)
    print(f"FPS: {fps}, Frames: {number_of_frames}")

    for frame_number in tqdm(range(number_of_frames)):
        _, image = vidcap.read()
        img_filename = path.join(output_folder, f"{str(frame_number).zfill(4)}.jpg")
        print(f"Processing frame {frame_number}: {img_filename}")
        cv2.imwrite(img_filename, image)
    return fps


basePath = os.path.abspath(".")

# 需要的算法框架目录
wav2lipFolderName = 'Wav2Lip-master'
gfpganFolderName = 'GFPGAN-master'
wav2lipPath = os.path.join(basePath, wav2lipFolderName)
gfpganPath = os.path.join(basePath, gfpganFolderName)

# 确定需要制作的用户视频
userPath = "test"


def create_videos_from_frames(frames_folder, output_folder, fps, batch_size):
    dir_list = os.listdir(frames_folder)
    dir_list.sort()

    restored_imgs_folder = None
    for folder in dir_list:
        if folder == 'restored_imgs':
            restored_imgs_folder = os.path.join(frames_folder, folder)
            break

    if restored_imgs_folder is None:
        print("restored_imgs folder not found")
        return 0

    img_list = [file for file in os.listdir(restored_imgs_folder)]
    img_list.sort()
    print(f"frames_folder: {img_list}")
    batch = 0
    size = None

    for i in tqdm(range(0, len(img_list), batch_size)):
        img_array = []
        start, end = i, i + batch_size
        print(f"Processing {start} {end}")

        for filename in tqdm(img_list[start:end]):
            filename = os.path.join(restored_imgs_folder, filename)
            print(f"filename: {filename}")
            img = cv2.imread(filename)  # 使用绝对路径
            print(f"img: {img}")
            if img is None:
                print(f"Invalid frame: {filename}")
                continue
            height, width, layers = img.shape
            size = (width, height)
            img_array.append(img)

        output_file = os.path.join(output_folder, f'batch_{str(batch).zfill(4)}.mp4')
        out = cv2.VideoWriter(output_file, cv2.VideoWriter_fourcc(*'DIVX'), fps, size)
        batch = batch + 1

        for i in range(len(img_array)):
            out.write(img_array[i])
        out.release()

    return batch  # 返回批次数


def concatenate_videos(output_folder, batch_count, concat_filepath, output_filepath):
    with open(concat_filepath, "w", encoding='utf8') as concat_text_file:
        for ips in range(batch_count):
            concat_text_file.write(f"file batch_{str(ips).zfill(4)}.mp4\n")

    cmd = f"ffmpeg -y -f concat -i {concat_filepath} -c copy {output_filepath}"
    os.system(cmd)


def merge_audio_and_video(video_path, audio_path, output_path):
    cmd = f"ffmpeg -y -i {video_path} -i {audio_path} -map 0 -map 1:a -c:v copy -shortest {output_path}"
    os.system(cmd)


userAudioPathList = os.listdir(os.path.join("inputs", userPath, "source_audio"))

for sourceAudioName in userAudioPathList:
    title = sourceAudioName.split(".")[-2]
    userVideoPathList = os.listdir(os.path.join("inputs", userPath, "source_video"))
    sourceVideoName = random.sample(userVideoPathList, 1)[0]

    outputPath = os.path.join(basePath, "outputs", title)
    if not os.path.exists(outputPath):
        os.makedirs(outputPath)

    inputAudioPath = os.path.join(basePath, "inputs", userPath, "source_audio", sourceAudioName)
    inputVideoPath = os.path.join(basePath, "inputs", userPath, "source_video", sourceVideoName)
    lipSyncedOutputPath = os.path.join(basePath, 'outputs', title, "result.mp4")

    process_video_with_wav2lip(inputVideoPath, inputAudioPath, lipSyncedOutputPath)

    unProcessedFramesFolderPath = os.path.join(outputPath, 'frames')
    if not os.path.exists(unProcessedFramesFolderPath):
        os.makedirs(unProcessedFramesFolderPath)

    fps = extract_frames_from_video(lipSyncedOutputPath, unProcessedFramesFolderPath)

    restoredFramesPath = os.path.join(outputPath, 'restored_imgs')
    if not os.path.exists(restoredFramesPath):
        os.makedirs(restoredFramesPath)

    process_images_with_gfpgan(unProcessedFramesFolderPath, restoredFramesPath)

    processedVideoOutputPath = outputPath
    batch = create_videos_from_frames(restoredFramesPath, processedVideoOutputPath, fps, batch_size=600)
    concatTextFilePath = os.path.join(outputPath, "concat.txt")
    concatedVideoOutputPath = os.path.join(outputPath, "concated_output.mp4")
    concatenate_videos(outputPath, batch, concatTextFilePath, concatedVideoOutputPath)

    finalProcessedOutputVideo = os.path.join(processedVideoOutputPath, 'final_with_audio.mp4')
    merge_audio_and_video(concatedVideoOutputPath, inputAudioPath, finalProcessedOutputVideo)
