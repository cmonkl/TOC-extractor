import asyncio
import io
import logging
import sys

import aiohttp
from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.client.bot import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import BufferedInputFile, FSInputFile, Message
from aiogram.utils.markdown import hbold
from aiogram.utils.chat_action import ChatActionSender
import fitz
import json
from config import TOKEN_API

# All handlers should be attached to the Router (or Dispatcher)
dp = Dispatcher()

# Setting up logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

# info messages to admins
# @dp.startup()
# async def start_bot(bot: Bot) -> None:
#     await bot.send_message(123456789, text="Bot is started")
#     logging.info("Bot is started")


# @dp.shutdown()
# async def stop_bot(bot: Bot) -> None:
#     await bot.send_message(123456789, text="Bot is stopped")
#     logging.info("Bot is stopped")


async def send_pdf_to_server(file: types.File, bot: Bot):
    """Sending a PDF-file to ML-pipeline"""
    url = "http://127.0.0.1:5000/process"
    timeout = aiohttp.ClientTimeout(total=900)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        file_data = await bot.download_file(file.file_path)
        data = aiohttp.FormData()
        data.add_field("file", file_data, filename=file.file_unique_id)
        try:
            async with session.post(url, data=data) as response:
                # await asyncio.sleep(10)
                if response.status == 200:
                    # Retrieving a processed file from the server
                    processed_file = await response.read()
                    return processed_file
                else:
                    # Handling errors
                    logger.error(
                        f"Failed to process file, server response status is {response.status}"
                    )
                    return None
        except Exception as e:
            logger.exception(f"An error occurred while processing file:\n{e}")
            return None


@dp.message(F.document.mime_type == "application/pdf")
async def getting_file_handler(message: Message, bot: Bot) -> None:
    """Handling PDF-files"""
    file_id = message.document.file_id
    orig_file_name = message.document.file_name
    file = await bot.get_file(file_id)

    downloaded_file = await bot.download_file(file.file_path)
    pdf_bytes = io.BytesIO(downloaded_file.getvalue())
    try:
        with fitz.Document(stream=pdf_bytes, filetype="pdf") as doc:
            toc = doc.get_toc()
            if len(toc) == 0:
                await message.reply(
                    f"Nice pdf-file, {hbold(message.from_user.full_name)}, I will process it..."
                )
                # send file to ML-pipeline
                async with ChatActionSender.upload_document(
                    chat_id=message.chat.id, bot=bot
                ):
                    processed_pdf = await send_pdf_to_server(file, bot)

                    if processed_pdf:
                        # return file to sender
                        await message.reply_document(
                            document=BufferedInputFile(
                                processed_pdf,
                                filename=f"processed_{orig_file_name}",
                            ),
                            caption="Here is your processed file.",
                        )
                    else:
                        # errors handling if file can't be processed with ML-pipeline
                        await message.reply("Sorry, I've got some problems...")
            else:
                await message.reply(
                    "This document already has a table of contents, I will not process it."
                )
    except Exception as e:
        logger.exception(f"An error occurred while reading a pdf-file: \n {e}")
        await message.reply(
            "It seems, this document is not a valid PDF-document."
        )


@dp.message(F.content_type.in_({"document"}))
async def getting_file_handler(message: Message) -> None:
    """Handling other types of files"""
    await message.reply(
        f"Sorry, only pdf-files are supported, {hbold(message.from_user.full_name)}!"
    )


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
    This handler receives messages with `/start` command
    """
    await message.answer(f"Hello, dear {hbold(message.from_user.full_name)}!")


@dp.message()
async def echo_handler(message: types.Message) -> None:
    """
    Handler will forward receive a message back to the sender

    By default, message handler will handle all message types (like a text, photo, sticker etc.)
    """
    try:
        # Send a copy of the received message
        await message.send_copy(chat_id=message.chat.id)
    except TypeError:
        # But not all the types is supported to be copied so need to handle it
        await message.answer("Nice try!")


async def main() -> None:
    # Initialize Bot instance with a default parse mode which will be passed to all API calls
    bot = Bot(
        TOKEN_API, default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    # And the run events dispatching
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
