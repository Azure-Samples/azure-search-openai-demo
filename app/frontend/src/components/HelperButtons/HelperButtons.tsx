import { useState } from "react";
import { Stack, Tooltip } from "@fluentui/react";
import { Button } from "react-bootstrap";
import { RequestType } from "../../api";

import styles from "./HelperButtons.module.css";

interface Props {
    onRequest: (question: string, requestType: RequestType) => void;
}

export const HelperButtons = ({ onRequest }: Props) => {
    const [information, setInformation] = useState<string>("");

    const sendRequest = (requestType: RequestType) => {};

    const handleFileChange = (requestType: RequestType) => (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files ? event.target.files[0] : null;
        // sendRequest();
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

            <Button className={styles.helperButton} onClick={() => sendRequest("generate_iog")}>
                Generate Island of Agreement
            </Button>
        </Stack>
    );
};
