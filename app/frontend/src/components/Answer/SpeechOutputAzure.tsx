import { useState } from "react";

import { IconButton } from "@fluentui/react";
import { getSpeechApi } from "../../api";

interface Props {
    answer: string;
    urls: (string | null)[];
    updateSpeechUrls: (urls: (string | null)[]) => void;
    index: number;
    audio: HTMLAudioElement;
    isPlaying: boolean;
    setIsPlaying: (isPlaying: boolean) => void;
    isStreaming: boolean;
}

export const SpeechOutputAzure = ({ answer, urls, updateSpeechUrls, index, audio, isPlaying, setIsPlaying, isStreaming }: Props) => {
    const [isLoading, setIsLoading] = useState(false);
    const [localPlayingState, setLocalPlayingState] = useState(false);

    const playAudio = async (url: string) => {
        audio.src = url;
        await audio
            .play()
            .then(() => {
                audio.onended = () => setIsPlaying(false);
                setIsPlaying(true);
                setLocalPlayingState(true);
            })
            .catch(() => {
                alert("Failed to play speech output.");
                console.error("Failed to play speech output.");
                setIsPlaying(false);
                setLocalPlayingState(false);
            });
    };

    const startOrStopSpeech = async (answer: string) => {
        if (isPlaying) {
            audio.pause();
            audio.currentTime = 0;
            setIsPlaying(false);
            setLocalPlayingState(false);
            return;
        }
        if (urls[index]) {
            playAudio(urls[index]);
            return;
        }
        setIsLoading(true);
        await getSpeechApi(answer).then(async speechUrl => {
            if (!speechUrl) {
                alert("Speech output is not available.");
                console.error("Speech output is not available.");
                return;
            }
            setIsLoading(false);
            updateSpeechUrls(urls.map((url, i) => (i === index ? speechUrl : url)));
            playAudio(speechUrl);
        });
    };

    const color = localPlayingState ? "red" : "black";
    return isLoading ? (
        <IconButton style={{ color: color }} iconProps={{ iconName: "Sync" }} title="Loading" ariaLabel="Loading answer" disabled={true} />
    ) : (
        <IconButton
            style={{ color: color }}
            iconProps={{ iconName: "Volume3" }}
            title="Speak answer"
            ariaLabel="Speak answer"
            onClick={() => startOrStopSpeech(answer)}
            disabled={isStreaming}
        />
    );
};
