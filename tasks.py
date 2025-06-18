import os
import uuid
import shutil
import subprocess
from datetime import datetime, timezone
from pydub import AudioSegment
from pydub.effects import low_pass_filter
from dotenv import load_dotenv
load_dotenv()
# Logger use
from voice_studio_stack.logger.logging_tool import get_logger
logger = get_logger()

from .celery_config import make_celery

from voice_studio_stack.database.mongodb import save_metadata_tts
from voice_studio_stack.omni_voice_lib.services.tts_service.tts_process import tts_generation
from voice_studio_stack.storage.local_storage import gen_local_key
from voice_studio_stack.storage.s3_storage import gen_s3_key
from voice_studio_stack.storage.s3_storage import gen_s3_key, get_presigned_url
from voice_studio_stack.iam.keycloak import get_username_by_user_id

celery_app = make_celery()

@celery_app.task(name="tasks.voice_tts_task")
def voice_tts_task(
    local_flag: bool,
    user_id: str,
    prompt: str,
    tmp_audio_path: str,
    voice: str,
    language: str,
    speed: float,
    boost: bool
    ):

    try:
        # Step 1: Unique filename inits.
        print(">>> [STAGE 1] Generating filenames and metadata")
        logger.info(">>> [STAGE 1] Generating filenames and metadata")
        timestamp = f"{datetime.now(tz=timezone.utc).strftime('%Y%m%d_%H%M%S')}" # UTC timestamp
        unique_filename = f"{timestamp}_{uuid.uuid4().hex[:8]}"
        service = "tts"

        # Step 2: Save input to local
        print(">>> [STAGE 2] Saving input files to local storage")
        logger.info(">>> [STAGE 2] Saving input files to local storage")
        input_audio_local = gen_local_key(user_id, service, "in", unique_filename, ".wav", tmp_audio_path)

        # Step 3: Save input to S3
        print(">>> [STAGE 3] Uploading input files to S3")
        logger.info(">>> [STAGE 3] Uploading input files to S3")
        input_audio_s3 = gen_s3_key(user_id, service, "in", unique_filename, ".wav", input_audio_local["file_path"])

        # Step 4: Run TTS model
        print(">>> [STAGE 4] Running TTS model")
        logger.info(">>> [STAGE 4] Running TTS model")
        output_audio_path = tts_generation(prompt=prompt, audio_path=tmp_audio_path, language=language) # PROCESSING LINE

        # Step 5: Adjust speed (in-place)
        if 0.7 <= speed <= 1.2 and speed != 1:
            print(">>> [STAGE 5] Changing audio speed")
            logger.info(">>> [STAGE 5] Changing audio speed")
            temp_path = output_audio_path.replace(".wav", "_temp.wav")
            subprocess.run([
                "ffmpeg", "-y", "-i", output_audio_path,
                "-filter:a", f"atempo={speed}", "-vn", temp_path
            ], check=True)
            shutil.move(temp_path, output_audio_path)

        # Step 6: Apply speaker boost (in-place)
        if boost:
            print(">>> [STAGE 6] Applying speaker boost")
            logger.info(">>> [STAGE 6] Applying speaker boost")
            audio = AudioSegment.from_file(output_audio_path, format="wav")
            bass = low_pass_filter(audio, cutoff=150)
            bass = bass + 10
            enhanced = audio.overlay(bass)
            boosted_temp_path = output_audio_path.replace(".wav", "_boosted.wav")
            enhanced.export(boosted_temp_path, format="wav")
            shutil.move(boosted_temp_path, output_audio_path)

        # Step 7: Save output to local
        print(">>> [STAGE 7] Saving output files to local storage")
        logger.info(">>> [STAGE 7] Saving output files to local storage")
        output_audio_local = gen_local_key(user_id, service, "out", unique_filename, ".wav", output_audio_path)

        # Step 8: Save output to s3
        print(">>> [STAGE 8] Uploading output files to S3")
        logger.info(">>> [STAGE 8] Uploading output files to S3")
        output_audio_s3 = gen_s3_key(user_id, service, "out", unique_filename, ".wav", output_audio_local["file_path"])

        # Step 9: Save metadata to MongoDB
        print(">>> [STAGE 9] Saving metadata to MongoDB")
        logger.info(">>> [STAGE 9] Saving metadata to MongoDB")
        configs = {
            "model_name": "lucataco/xtts-v2:684...55e",
            "language": language,
            "speed": speed,
            "boost": boost
        }
        username = get_username_by_user_id(user_id)
        save_metadata_tts(user_id=user_id,
                          username=username,
                          timestamp=timestamp,
                          prompt=prompt,
                          input_audio=input_audio_s3,
                          output_audio=output_audio_s3,
                          configs=configs,
                          voice=voice)
        
        # Step 10: Removing the temp and local files (if local_flag is false)
        print(">>> [STAGE 10] Cleaning up temporary files")
        logger.info(">>> [STAGE 10] Cleaning up temporary files")
        os.remove(tmp_audio_path)
        os.remove(output_audio_path)
        if local_flag:
            os.remove(input_audio_local["file_path"])
            os.remove(output_audio_local["file_path"])

        # Step 11: Returning the response
        input_audio_url = get_presigned_url(s3_key=input_audio_local["file_key"])
        output_audio_url = get_presigned_url(s3_key=output_audio_local["file_key"])
        print(">>> [STAGE 11] Returning output links")
        logger.info(">>> [STAGE 11] Returning output links")
        return {
            "prompt": prompt,
            "voice": voice,
            "input_audio_key": input_audio_local["file_key"],
            "output_audio_key": output_audio_local["file_key"],
            "download_links": {
                "input_audio": input_audio_url,
                "output_audio": output_audio_url
                }}
    except Exception as e:
        print(f">>> [ERROR] Exception occurred: {e}")
        logger.exception(f">>> [ERROR] Exception during TTS: {e}")
        raise ValueError(f"Error during TTS: {e}")
