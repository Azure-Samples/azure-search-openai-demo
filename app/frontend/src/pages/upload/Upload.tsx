import { useRef, useState, useMemo } from "react";

import styles from "./Upload.module.css";

import { askApi, ChatAppResponse, ChatAppRequest, RetrievalMode, uploadFilesApi, UploadFilesRequest } from "../../api";

import { AnalysisPanelTabs } from "../../components/AnalysisPanel";

import { useLogin, getToken } from "../../authConfig";
import { useMsal } from "@azure/msal-react";
import { useDropzone } from "react-dropzone";
import $ from "jquery";

const baseStyle = {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    padding: "20px",
    borderWidth: 2,
    borderRadius: 2,
    borderColor: "#eeeeee",
    borderStyle: "dashed",
    backgroundColor: "#fafafa",
    color: "#bdbdbd",
    outline: "none",
    transition: "border .24s ease-in-out"
};

const focusedStyle = {
    borderColor: "#2196f3"
};

const acceptStyle = {
    borderColor: "#00e676"
};

const rejectStyle = {
    borderColor: "#ff1744"
};
export function Component(): JSX.Element {
    const barRef = useRef<HTMLDivElement>(null);
    const [uploadedFiles, setUploadedFiles] = useState<any[]>([]);

    const { getRootProps, getInputProps, isFocused, isDragAccept, isDragReject } = useDropzone({
        onDrop: acceptedFiles => {
            setUploadedFiles(acceptedFiles);
        },
        accept: {
            "application/pdf": [".pdf"]
        },
        multiple: true
    });

    const style = useMemo<any>(
        () => ({
            ...baseStyle,
            ...(isFocused ? focusedStyle : {}),
            ...(isDragAccept ? acceptStyle : {}),
            ...(isDragReject ? rejectStyle : {})
        }),
        [isFocused, isDragAccept, isDragReject]
    );

    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [error, setError] = useState<unknown>();

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
                {/* <FileUploader classes="file-uploader" name="file" types={fileTypes} multiple /> */}
                <div {...getRootProps({ style })}>
                    <input {...getInputProps()} name="file" />
                    <p>Drag and drop files here or click to browse.</p>
                    <ul>
                        {uploadedFiles!.map(file => (
                            <li key={file.name}>{file.name}</li>
                        ))}
                    </ul>
                </div>
                <button type="submit">Upload</button>
            </form>
            <div className={styles.uploadProgress} onClick={progressMove}>
                <div className={styles.uploadBar} ref={barRef}></div>
            </div>
        </div>
    );
}

Component.displayName = "Upload";
