from jcba_receiver.audio import mp3_transcoder_command


def test_mp3_transcoder_command_streams_pipe_input_and_output():
    command = mp3_transcoder_command()

    assert command[0] == "ffmpeg"
    assert command[command.index("-i") + 1] == "pipe:0"
    assert command[-2:] == ["mp3", "pipe:1"]
