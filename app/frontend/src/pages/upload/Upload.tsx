import { useRef, useState } from "react";

import styles from "./Upload.module.css";

import { askApi, ChatAppResponse, ChatAppRequest, RetrievalMode, uploadFilesApi, UploadFilesRequest } from "../../api";

import { AnalysisPanelTabs } from "../../components/AnalysisPanel";

import { useLogin, getToken } from "../../authConfig";
import { useMsal } from "@azure/msal-react";
import { FileUploader } from "react-drag-drop-files";
import $ from "jquery";

const fileTypes = ["PDF"];
export function Component(): JSX.Element {
    const barRef = useRef<HTMLDivElement>(null);

    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [error, setError] = useState<unknown>();
    const [answer, setAnswer] = useState<ChatAppResponse>();

    const [activeCitation, setActiveCitation] = useState<string>();
    const [activeAnalysisPanelTab, setActiveAnalysisPanelTab] = useState<AnalysisPanelTabs | undefined>(undefined);

    const client = useLogin ? useMsal().instance : undefined;

    const makeApiRequest = async (files: any) => {
        error && setError(undefined);
        setIsLoading(true);

        $.ajax({
            url: `/upload`,
            type: "POST",
            data: files,
            processData: false,
            contentType: false,
            // xhr for progress of this form upload
            xhr: function () {
                var xhr = new XMLHttpRequest();
                xhr.upload.addEventListener(
                    "progress",
                    function (evt) {
                        if (evt.lengthComputable) {
                            var percentComplete = (evt.loaded / evt.total) * 100;
                            console.log(percentComplete);
                            barRef.current!.style.width = percentComplete + "%";
                        }
                    },
                    false
                );
                return xhr;
            },
            success: function (data) {
                console.log("success");
                console.log(data);
                setIsLoading(false);
            },
            error: function (e) {
                console.log("error");
                console.log(e);
                setIsLoading(false);
                setError(e);
            }
        });
    };

    const handleFilesSubmit = (e: any) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        makeApiRequest(formData);
    };

    const progressMove = () => {
        const elem = barRef.current;
        let width = 1;
        const id = setInterval(frame, 50);
        function frame() {
            if (width >= 100) {
                clearInterval(id);
            } else {
                width++;
                elem!.style.width = width + "%";
            }
        }
    };

    return (
        <div className={styles.uploadContainer}>
            <form method="POST" encType="multipart/form-data" onSubmit={handleFilesSubmit}>
                <FileUploader classes="file-uploader" name="file" types={fileTypes} multiple />
                <button type="submit">Submit</button>
            </form>
            <div className={styles.uploadProgress} onClick={progressMove}>
                <div className={styles.uploadBar} ref={barRef}></div>
            </div>
        </div>
    );
}

Component.displayName = "Upload";
