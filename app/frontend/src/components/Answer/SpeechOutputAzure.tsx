import { useState } from "react";

import { IconButton } from "@fluentui/react";
import { getSpeechApi, SpeechConfig } from "../../api";

interface Props {
    answer: string;
    speechConfig: SpeechConfig;
    index: number;
    isStreaming: boolean;
}

export const SpeechOutputAzure = ({ answer, speechConfig, index, isStreaming }: Props) => {
    const [isLoading, setIsLoading] = useState(false);
    const [localPlayingState, setLocalPlayingState] = useState(false);

    const playAudio = async (url: string) => {
        speechConfig.audio.src = url;
        await speechConfig.audio
            .play()
            .then(() => {
                speechConfig.audio.onended = () => {
                    speechConfig.setIsPlaying(false);
                    setLocalPlayingState(false);
                };
                speechConfig.setIsPlaying(true);
                setLocalPlayingState(true);
            })
            .catch(() => {
                alert("Failed to play speech output.");
                console.error("Failed to play speech output.");
                speechConfig.setIsPlaying(false);
                setLocalPlayingState(false);
            });
    };

    const startOrStopSpeech = async (answer: string) => {
        if (speechConfig.isPlaying) {
            speechConfig.audio.pause();
            speechConfig.audio.currentTime = 0;
            speechConfig.setIsPlaying(false);
            setLocalPlayingState(false);
            return;
        }
        if (speechConfig.speechUrls[index]) {
            playAudio(speechConfig.speechUrls[index]);
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
            speechConfig.setSpeechUrls(speechConfig.speechUrls.map((url, i) => (i === index ? speechUrl : url)));
            playAudio(speechUrl);
        });
    };

    const color = localPlayingState ? "red" : "black";

    // We always preload the Sync icon in hidden mode so that there's no visual glitch when icon changes
    return isLoading ? (
        <IconButton style={{ color: color }} iconProps={{ iconName: "Sync" }} title="Loading speech" ariaLabel="Loading speech" disabled={true} />
    ) : (
        <>
            <IconButton iconProps={{ iconName: "Sync" }} ariaHidden={true} disabled={true} style={{ display: "none" }} />
            <IconButton
                style={{ color: color }}
                iconProps={{ iconName: "Volume3" }}
                title="Speak answer"
                ariaLabel="Speak answer"
                onClick={() => startOrStopSpeech(answer)}
                disabled={isStreaming}
            />
        </>
    );
};
