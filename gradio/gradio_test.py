import gradio as gr
import base64
import time
from PIL import Image
from typing import Union
from qwen_omni_utils import process_mm_info
from modelscope import Qwen2_tOmniModel, Qwen2_5OmniProcessor
import torch

model_name_or_path = ""

model = Qwen2_tOmniModel.from_pretrained(model_name_or_path, torch_dtype=torch.bfloat16, device_map="auto")
processor = Qwen2_5OmniProcessor.from_pretrained(model_name_or_path, use_fast=True)

def encode_image(image_path):
    with open(image_path, "rb") as f:
        encoded_image = base64.b64encode(f.read()).decode("utf-8")

    return encoded_image

def process(image_input, chat_input):
    if image_input is None:
        return "请上传一张图片"

    base64_qwen = f"data:image;base64,{encode_image(image_input)}"
    message = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "image": base64_qwen,
                },
                {
                    "type": "text",
                    "text": chat_input if chat_input else "Describe this image."
                }
            ]
        }
    ]

    text = processor.apply_chat_template(
        message, tokenize=False, add_generation_prompt=False
    )
    audios_input, images_input, videos_input = process_mm_info(message, use_audio_in_video=True)
    inputs = processor(
        text=text,
        images=images_input,
        videos=videos_input,
        padding=True,
        return_tensors="pt"
    )

    inputs = inputs.to(model.device).to(model.dtype)

    print("start time: ", time.time())
    generated_ids = model.generate(**inputs, max_new_tokens=8192)
    print("end time: ", time.time)

    generated_ids_trimed = [out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)]
    output_text = processor.batch_decode(generated_ids_trimed, skip_special_tokens=True, clean_up_tokenization_spaces=False)
    print(output_text)

with gr.Blocks(theme=gr.themes.Default()) as demo:
    gr.Markdown("# 演示Demo")

    state = gr.State({})

    with gr.Accordion("Settings", open=True):
        with gr.Row():
            with gr.Column(scale=20):
                image_input = gr.Image(type='filepath', label='Upload image')
        
        with gr.Row():
            with gr.Column(scale=8):
                chat_output = gr.Textbox(show_label=False, placeholder="Image Desc output", container=False)
        
        with gr.Row():
            with gr.Column(scale=8):
                chat_input = gr.Textbox(show_label=False, placeholder="Type a message to send to server + X ...", container=False)
            with gr.Column(scale=1, min_width=50):
                submit_button = gr.Button(value="Send", variant="primary")
            with gr.Column(scale=1, min_width=50):
                stop_button = gr.Button(value="Stop", variant="secondary")

        submit_button.click(
            fn=process,
            inputs=[
                image_input,
                chat_input,
            ],
            outputs=[
                chat_output
            ]
        )


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7890)