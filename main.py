@dp.message_handler(state=GPTState.question)
async def gpt_answer(message: types.Message, state: FSMContext):
    if message.text == "◀️ Назад":
        await state.finish()
        await message.answer("Главное меню", reply_markup=main_kb)
        return

    await message.answer("🤖 Думаю...")

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # или gpt-4 при наличии доступа
            messages=[
                {"role": "system", "content": "Ты — эксперт по 3D-печати и проектированию."},
                {"role": "user", "content": message.text}
            ]
        )
        answer = response.choices[0].message.content
        await message.answer(f"🧠 Ответ:\n{answer}", reply_markup=main_kb)

        # лог в Google Sheet (если есть доступ)
        if 'log_sheet' in globals() and log_sheet:
            row_id = len(log_sheet.get_all_values())
            log_sheet.append_row([
                row_id,
                message.from_user.id,
                message.text,
                answer,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ])

    except Exception as e:
        await message.answer(f"⚠️ Ошибка GPT:\n{e}")
        logging.exception(e)
    finally:
        await state.finish()
