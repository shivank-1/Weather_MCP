# Endpoint: TEXT OVER SPEECH
@app.post("/synthesize")
async def synthesize(
    prompt: str = Form(...),
    audio_file : UploadFile = File(None),
    voice: str = Form(None),
    language: str = Form("en"),
    speed: float = Form(1.0),  # 0.7–1.2
    boost: bool = Form(True
    token: str = Depends(get_user_ioles)
    ):
    
    Generate speech from text using TTS model.
    """
    try:
        if not prompt:
            raise HTTPException(status_code=400, detail="Text prompt is required.")
        if (not voice and not audio_file) or (voice and audio_file):
            raise HTTPException(status_code=400, detail="Provide either a voice selection OR an audio file, not both.")
        if not (0.7 <= speed <= 1.2):
            raise HTTPException(status_code=400, detail="Speed must be between 0.7 and 1.2, both inclusive.")
        # JWT token validation and user role extraction
        user_id = token["user_id"]
        user_roles = token["roles"]
        logger.info(f"user_id: {user_id} | roles: {user_roles} | service: tts")
        user_role = next((r for r in ["free", "premium", "enterprise"] if r in user_roles), None)
        if not user_role:
            raise HTTPException(status_code=403, detail="Invalid user role.")
        
        audio_count = get_user_audio_count(user_id)
        if user_role == "free" and audio_count >= ROLE_LIMITS["free"]:
            raise HTTPException(status_code=403, detail="Free users can upload only limited audio. Please upgrade!")
        if user_role == "premium" and audio_count >= ROLE_LIMITS["premium"]:
            raise HTTPException(status_code=403, detail="Premium users reached the audio upload limit.")
        if user_role == "enterprise" and audio_count >= ROLE_LIMITS["enterprise"]:
            raise HTTPException(status_code=403, detail="Enterprise users reached the audio upload limit.")

        if audio_file:
            tmp_audio_path = save_file_temp(audio_file)
            voice = "N/A"
        elif voice and voice != "N/A":
            audio_url = fetch_public_data(voice)["audio_url"]
            try:
                tmp_audio_path = save_file_from_url(audio_url)
            except Exception:
                raise HTTPException(status_code=400, detail="Failed to fetch audio from URL.")
        else:
            raise HTTPException(status_code=400, detail="No valid input speaker selection provided.")

        task_result = voice_tts_task.delay(
            local_flag=True,
            user_id=user_id,
            prompt=prompt,
            tmp_audio_path=tmp_audio_path,
            voice=voice,
            language=language,
            speed=speed,
            boost=boost
            )

        logger.info(f"TTS task ID: {task_result.id}")
        return {"task_id": task_result.id}
    except Exception as e:
        logger.error(f"Error during TTS synthesis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error during TTS synthesis: {str(e)}")
    
# Endpoint: GET TASK RESULT
@app.get("/task-status/{task_id}")
async def get_task_status(
    task_id: str, 
    token: str = Depends(get_user_id_roles), 
    service: str = Query(...) 
    ):
    """
    Get the response of a task by its ID.
    Checks the status of a task and returns its result if completed.
    """

    # JWT token validation and user role extraction
    user_id = token["user_id"]
    user_roles = token["roles"]
    logger.info(f"user_id: {user_id} | roles: {user_roles} | task_id: {task_id}")

    task_map = {
        "denoise": voice_denoise_task,
        "effects": voice_effects_task,
        "voice_changer": voice_changer_task,
        "tts": voice_tts_task,
        "audiobook": voice_audiobook_task
    }

    task_cls = task_map.get(service)
    task_result = task_cls.AsyncResult(task_id)
    state = task_result.state

    if state == "FAILURE":     # Handle a failed task without re-raising the exception.
        error_message = str(task_result.result)  # This is the error that occurred in the task
        return {"status": "failed", "result": error_message}
    
    elif state == "SUCCESS":
        # Update audio count for user_id, since enterprise roles can create unlimited audio
        if "free" in user_roles:
            increment_user_audio_count(user_id)
            print(f"audio count for user {user_id} updated.")  # Debugging line
        elif "premium" in user_roles:
            increment_user_audio_count(user_id)
            print(f"audio count for user {user_id} updated.")
        elif "enterprise" in user_roles:
            increment_user_audio_count(user_id)
            print(f"audio count for user {user_id} updated.")
        return {"status": "completed", "result": task_result.result}
    else:
        return {"status": state.lower(), "result": None}