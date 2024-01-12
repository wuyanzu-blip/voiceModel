# from dotenv import load_dotenv
import dashscope
from dashscope.audio.tts import SpeechSynthesizer

dashscope.api_key='sk-01f79255de394c22a8ca88b96a0afaf1'

from moviepy.editor import VideoFileClip,AudioFileClip
from moviepy.audio.io.AudioFileClip import AudioFileClip

import cv2
import base64
import io
import openai
import os
import requests
import streamlit as st
import tempfile

# load_dotenv()

##1.Turn video into frames
def video_to_frames(video_file):
    #save the upload video file to a temporary file
    with tempfile.NamedTemporaryFile(delete=False,suffix='.mp4') as tmpfile:
        tmpfile.write(video_file.read())
        video_filename=tmpfile.name
    
    video_duration=VideoFileClip(video_filename).duration
    video=cv2.VideoCapture(video_filename)
    base64Frame=[]
    
    while video.isOpened():
        success, frame=video.read()
        if not success:
            break
        _,buffer=cv2.imencode('.jpg',frame)
        base64Frame.append(base64.b64encode(buffer).decode("utf-8"))
    
    video.release()
    print(len(base64Frame),"frames read.")
    return base64Frame,video_filename,video_duration

def download_audio(url):
    try:
        # 发送 GET 请求下载音频文件
        response = requests.get(url, stream=True)
        response.raise_for_status()

        # 创建一个临时目录
        temp_dir = tempfile.mkdtemp()

        # 提取文件名
        filename = url.split("/")[-1]

        # 拼接保存路径
        file_path = f"{temp_dir}/{filename}"

        # 将文件保存到临时目录
        with open(file_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)

        return file_path

    except Exception as e:
        print(f"下载音频文件失败: {e}")
        return None

##2.Generate stories based on frames with gpt4v
def frames_to_story(base64Frames,prompt,api_key):
    PROMPT_MESSAGES=[
        {
            "role":"user",
            "content":[
                prompt,
                *map(lambda x:{"image":x,"resize":768},base64Frames[0::50]),
            ],
        },
    ]
    params={
        "model":"gpt-4-vision-preview",
        "messages":PROMPT_MESSAGES,
        "api_key":api_key,
        "headers":{"Openai-Version":"2020-11-07"},
        "max_tokens":500,
    }
    result=openai.ChatCompletion.create(**params)
    print(result.choices[0].message.content)
    return result.choices[0].message.content
##3.Generate voice over from stories
def text_to_audio(text,api_key,voice):
    response=requests.post(
        "https://api.openai.com/v1/audio/speech",
        headers={
            "Authorization":f"Bearer {api_key}",
        },
        json={
            "model":"tts-1",
            "input":text,
            "voice":voice,
            # "voice":"alloy",
        },
    )
    
    # nova 女年轻
    # alloy 男
    # alloy echo fable onyx nova shimmer
    
    #Check if the request was successful
    if response.status_code != 200:
        raise Exception("Request failed with status code")
    
    #Create an in-memory bytes buffer
    audio_bytes_io=io.BytesIO()
    #Write audio data to the in-memory bytes buffer
    for chunk in response.iter_content(chunk_size=1024*1024):
        audio_bytes_io.write(chunk)
        
    #Important : Seek to the start of the BytesIO buffer before returning
    audio_bytes_io.seek(0)
    
    #save audio to a temporary file
    with tempfile.NamedTemporaryFile(suffix=".wav",delete=False) as tmpfile:
        for chunk in response.iter_content(chunk_size=1024*1024):
            tmpfile.write(chunk)
        audio_filename=tmpfile.name
    
    return audio_filename,audio_bytes_io
##4.Merge videos & audio taudio_bytes_io
def merge_audio_video(video_filename,audio_filename,output_filename):
    print("Merging audio and video ...")
    #load the video file
    video_clip=VideoFileClip(video_filename)
    #load the audio file
    audio_clip=AudioFileClip(audio_filename)
    #set the audio of the video clip as the audio file
    final_clip=video_clip.set_audio(audio_clip)
    #write the result to a file (without audio)
    final_clip.write_videofile(output_filename,codec='libx264',audio_codec="aac")
    #close the clips
    video_clip.close()
    audio_clip.close()
    
    #return the path to the new video file
    return output_filename
##5.Streamlit UI
def main():
    st.set_page_config(page_title="xRunda GPT4V Demo Video Story Generator",page_icon="🎥")
    st.header("xRunda GPT4V Demo :bird:")
    
    openai_key=st.text_input("输入你的 OpenAI API key",type="password")
    if openai_key in ["",None]:
        st.write("API key 不能为空")
        exit()
        
    uploaded_file=st.file_uploader("选择视频文件",type=["mp4","avi"])

    option = st.selectbox(
    '选择你想要的音效',
    ('东北女声', '男声', '明哥', '光哥', '普通话'))
    classify = '';
    if option == '男声':
        classify = 'echo';
    elif option == '东北女声':
        classify = 'dongbeinv';
        st.write("试听链接：https://res.xrunda.com/paper-tts/1705027721wncoHt.mp3")
    elif option == '明哥':
        classify = 'ming';
        st.write("试听链接：https://res.xrunda.com/paper-tts/1705027124nTvciZ.mp3")
    elif option == '光哥':
        classify = 'guang';
        st.write("试听链接：https://res.xrunda.com/paper-tts/1705027189XDdwWl.mp3")
    elif option == '普通话':
        classify = 'custom';
        st.write("试听链接：https://res.xrunda.com/paper-tts/1705027238xJ48m5.mp3")
    # elif option == 'xxx':
    #     classify = 'onyx';
    if uploaded_file is not None:
        st.video(uploaded_file)
        # p='These are demonstration videos of the traditional woodworking piecing process.Create a short voiceover script that can be used along this video.'
        # p='这些都是传统木工拼接工艺的演示视频。制作一个简短的中文配音脚本，配合视频中的画面做内容描述，与该视频一起使用。'
        # p='这是一个儿童手工制作视频。生成一个简短的中文配音脚本，配合视频中的画面做内容描述，与该视频一起使用。内容尽量活泼轻松，不要过于严肃。'
        p='为视频生成一个简短的中文配音脚本，配合视频中的画面做内容描述，与该视频一起使用。内容尽量活泼轻松，不要过于严肃。'
        # p='这些是青年油画家陈曙丹的油画作品，生成一个简短的中文配音脚本，逐一讲解和分析一下每幅作品的画面美感和艺术性，以及作者在创作时候的思想状态。配合视频中的画面做内容描述，与该视频一起使用。直接生成配音脚本，不要回答我，请直接开始生成。'
        # p='These are frames of a quick product demo walkthrough.Create a short voiceover script that can be used along this video.'
        prompt=st.text_area(
            "Prompt",value=p
        )
    
    
    if st.button("生成",type="primary") and uploaded_file is not None:
        with st.spinner("生成中..."):
            base64Frame,video_filename,video_duration=video_to_frames(uploaded_file)
            if video_duration > 60:
                e = RuntimeError('视频超长会导致生成失败，请选择一分钟以内的视频')
                st.exception(e)
                exit()
            est_word_count=video_duration
            # est_word_count=video_duration*4
            final_prompt=prompt+f"(This video is ONLY {video_duration} seconds long.so make sure the voice over MUST be able to be explained in less that {est_word_count} words).Don't answer me, please start generating directly"
            text=frames_to_story(base64Frame,final_prompt,openai_key)
            # if 'text' not in st.session_state:
            #     st.session_state['text'] = text
            # if 'text' not in st.session_state:
            #     st.session_state.key = text
            st.write(text)
            if text is not None:
                st.write('(生成文案如果不正确或不满意，您可以重新点击生成)')
                if classify == 'ming':
                    response=requests.post(
                        "https://podcast-ai.xrunda.com/api/com_tts",
                        headers={
                            "Content-Type": "application/x-www-form-urlencoded;charset=utf-8", # 指定请求体为JSON格式
                        },
                        data={
                            "text":text,
                            "voice":"DS-Ming"
                        },
                    )
                    st.write('已为您生成音频与字幕，请点击链接查看')
                    voice = response.json()
                    st.write('音频：' + voice['data'][0])
                    st.write('字幕：' + voice['data'][1])
                    # 获取下载好的音频和视频文件
                    # filePath = download_audio('https://res.xrunda.com/paper-tts/1704958137gBj9fl.mp3')
                    filePath = download_audio(voice['data'][0])
                    output_video_filename=os.path.splitext(video_filename)[0]+"_output.mp4"
                    final_video_filename=merge_audio_video(video_filename,filePath,output_video_filename)
                    #display the result
                    st.video(final_video_filename)
                    
                    #clean up the temporary files
                    os.unlink(video_filename)
                    os.unlink(filePath)
                    os.unlink(final_video_filename)
                elif classify == 'guang':
                    response=requests.post(
                        "https://podcast-ai.xrunda.com/api/com_tts",
                        headers={
                            "Content-Type": "application/x-www-form-urlencoded;charset=utf-8", # 指定请求体为JSON格式
                        },
                        data={
                            "text":text,
                            "voice":"DS-Guang"
                        },
                    )
                    st.write('已为您生成音频与字幕，请点击链接查看')
                    voice = response.json()
                    st.write('音频：' + voice['data'][0])
                    st.write('字幕：' + voice['data'][1])
                    # 获取下载好的音频和视频文件
                    filePath = download_audio(voice['data'][0])
                    output_video_filename=os.path.splitext(video_filename)[0]+"_output.mp4"
                    final_video_filename=merge_audio_video(video_filename,filePath,output_video_filename)
                    #display the result
                    st.video(final_video_filename)
                    
                    #clean up the temporary files
                    os.unlink(video_filename)
                    os.unlink(filePath)
                    os.unlink(final_video_filename)
                elif classify == 'custom':
                    response=requests.post(
                        "https://podcast-ai.xrunda.com/api/com_tts",
                        headers={
                            "Content-Type": "application/x-www-form-urlencoded;charset=utf-8", # 指定请求体为JSON格式
                        },
                        data={
                            "text":text,
                            "voice":"zh-CN-YunyangNeural",
                            "rate":"5",
                            "volume":"5",
                        },
                    )
                    st.write('已为您生成音频与字幕，请点击链接查看')
                    voice = response.json()
                    st.write('音频：' + voice['data'][0])
                    st.write('字幕：' + voice['data'][1])
                    # 获取下载好的音频和视频文件
                    filePath = download_audio(voice['data'][0])
                    output_video_filename=os.path.splitext(video_filename)[0]+"_output.mp4"
                    final_video_filename=merge_audio_video(video_filename,filePath,output_video_filename)
                    #display the result
                    st.video(final_video_filename)
                    
                    #clean up the temporary files
                    os.unlink(video_filename)
                    os.unlink(filePath)
                    os.unlink(final_video_filename)
                elif classify == 'dongbeinv':
                    response=requests.post(
                        "https://podcast-ai.xrunda.com/api/com_tts",
                        headers={
                            "Content-Type": "application/x-www-form-urlencoded;charset=utf-8", # 指定请求体为JSON格式
                        },
                        data={
                            "text":'今天天气怎么样，这里是一润一达为您播报今天的天气，北京今天晴，最高气温四摄氏度，最低气温零下六摄氏度',
                            "voice":"zh-CN-liaoning-XiaobeiNeural",
                            "rate":"5",
                            "volume":"5",
                        },
                    )
                    st.write('已为您生成音频与字幕，请点击链接查看')
                    voice = response.json()
                    st.write('音频：' + voice['data'][0])
                    st.write('字幕：' + voice['data'][1])
                    # 获取下载好的音频和视频文件
                    filePath = download_audio(voice['data'][0])
                    output_video_filename=os.path.splitext(video_filename)[0]+"_output.mp4"
                    final_video_filename=merge_audio_video(video_filename,filePath,output_video_filename)
                    #display the result
                    st.video(final_video_filename)
                    
                    #clean up the temporary files
                    os.unlink(video_filename)
                    os.unlink(filePath)
                    os.unlink(final_video_filename)
                else:
                    # response=requests.post(
                    #     "https://podcast-ai.xrunda.com/api/com_tts",
                    #     headers={
                    #         "Content-Type": "application/x-www-form-urlencoded;charset=utf-8", # 指定请求体为JSON格式
                    #     },
                    #     data={
                    #         "text":text,
                    #         "voice":"zh-CN-YunyangNeural",
                    #         "rate":"5",
                    #         "volume":"5",
                    #     },
                    # )
                    # st.write('已为您生成音频与字幕，请点击链接查看')
                    # voice = response.json()
                    # st.write('音频：' + voice['data'][0])
                    # st.write('字幕：' + voice['data'][1])
                    #Generate audio from text
                    audio_filename,audio_bytes_io=text_to_audio(text,openai_key,classify)
                    #merge audio and video
                    output_video_filename=os.path.splitext(video_filename)[0]+"_output.mp4"

                    final_video_filename=merge_audio_video(video_filename,audio_filename,output_video_filename)
                    

                    #display the result
                    st.video(final_video_filename)
                    
                    #clean up the temporary files
                    os.unlink(video_filename)
                    os.unlink(audio_filename)
                    os.unlink(final_video_filename)
if __name__=="__main__":
    main()