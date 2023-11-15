import { useState } from "react";
import { Stack, Tooltip, on } from "@fluentui/react";
import { Button } from "react-bootstrap";
import { RequestType } from "../../api";

import styles from "./HelperButtons.module.css";

interface Props {
    onRequest: (question: string, requestType: RequestType, requestContent: string) => void;
}

export const HelperButtons = ({ onRequest }: Props) => {
    const handleFileChange = (requestType: RequestType) => (event: React.ChangeEvent<HTMLInputElement>) => {
        console.log("|handleFileChange| " + requestType + " file changed");
        const file = event.target.files ? event.target.files[0] : null;
        if (file) {
            const reader = new FileReader();

            reader.onload = (e: ProgressEvent<FileReader>) => {
                if (e.target && e.target.result) {
                    const content = e.target.result as string;
                    console.log("|handleFileChange| content: " + content);
                    if (requestType === "upload_background") {
                        onRequest("Provided the background information.", requestType, content);
                    } else if (requestType === "upload_additional") {
                        onRequest("Provided the additional information.", requestType, content);
                    }
                }
            };

            reader.readAsText(file);
        }
    };

    return (
        <Stack horizontal className={styles.buttonContainer}>
            <input type="file" onChange={handleFileChange("upload_background")} style={{ display: "none" }} id="upload_background" />
            <Button className={styles.helperButton} onClick={() => document.getElementById("upload_background")!.click()}>
                Upload Background Information
            </Button>

            <input type="file" onChange={handleFileChange("upload_additional")} style={{ display: "none" }} id="upload_additional" />
            <Button className={styles.helperButton} onClick={() => document.getElementById("upload_additional")!.click()}>
                Upload Additional Information
            </Button>

            <Button className={styles.helperButton} onClick={() => onRequest("Request Island of Agreement", "generate_iog", "placeholder")}>
                Generate Island of Agreement
            </Button>
        </Stack>
    );
};
