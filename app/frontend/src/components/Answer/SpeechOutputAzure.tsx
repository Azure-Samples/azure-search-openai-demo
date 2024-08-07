import { useState } from "react";

import { IconButton } from "@fluentui/react";
import { getSpeechApi } from "../../api";

interface Props {
    answer: string;
}

let audio = new Audio();

export const SpeechOutputAzure = ({ answer }: Props) => {
    const [isPlaying, setIsPlaying] = useState(false);

    const startOrStopSpeech = async (answer: string) => {
        if (isPlaying) {
            audio.pause();
            setIsPlaying(false);
            return;
        }
        await getSpeechApi(answer).then(async speechUrl => {
            if (!speechUrl) {
                alert("Speech output is not available.");
                console.error("Speech output is not available.");
                return;
            }
            audio = new Audio(speechUrl);
            await audio.play();
            audio.addEventListener("ended", () => {
                setIsPlaying(false);
            });
            setIsPlaying(true);
        });
    };

    const color = isPlaying ? "red" : "black";
    return (
        <IconButton
            style={{ color: color }}
            iconProps={{ iconName: "Volume3" }}
            title="Speak answer"
            ariaLabel="Speak answer"
            onClick={() => startOrStopSpeech(answer)}
        />
    );
};
