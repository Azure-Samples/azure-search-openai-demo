import { useState } from "react";

import { IconButton } from "@fluentui/react";

interface Props {
    url: string | null;
}

let audio = new Audio();

export const SpeechOutputAzure = ({ url }: Props) => {
    const [isPlaying, setIsPlaying] = useState(false);

    const startOrStopAudio = async () => {
        if (isPlaying) {
            audio.pause();
            setIsPlaying(false);
            return;
        }

        if (!url) {
            console.error("Speech output is not yet available.");
            return;
        }
        audio = new Audio(url);
        await audio.play();
        audio.addEventListener("ended", () => {
            setIsPlaying(false);
        });
        setIsPlaying(true);
    };

    const color = isPlaying ? "red" : "black";
    return (
        <IconButton
            style={{ color: color }}
            iconProps={{ iconName: "Volume3" }}
            title="Speak answer"
            ariaLabel="Speak answer"
            onClick={() => startOrStopAudio()}
            disabled={!url}
        />
    );
};
