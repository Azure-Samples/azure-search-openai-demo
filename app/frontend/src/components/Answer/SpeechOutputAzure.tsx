import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@fluentui/react-components";
import { ArrowSync24Regular, Speaker224Regular } from "@fluentui/react-icons";
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
    const { t } = useTranslation();

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
        <Button
            appearance="transparent"
            style={{ color: color }}
            icon={<ArrowSync24Regular />}
            title="Loading speech"
            aria-label="Loading speech"
            disabled={true}
        />
    ) : (
        <>
            <Button appearance="transparent" icon={<ArrowSync24Regular />} aria-hidden={true} disabled={true} style={{ display: "none" }} />
            <Button
                appearance="transparent"
                style={{ color: color }}
                icon={<Speaker224Regular />}
                title={t("tooltips.speakAnswer")}
                aria-label={t("tooltips.speakAnswer")}
                onClick={() => startOrStopSpeech(answer)}
                disabled={isStreaming}
            />
        </>
    );
};
