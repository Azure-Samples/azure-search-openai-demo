import { useRef, useState, useMemo } from "react";

import styles from "./Upload.module.css";
import { useDropzone } from "react-dropzone";
import $ from "jquery";

const WEBSOCKET_ENDPOINT = "ws://51.103.210.242/ws";

const baseStyle = {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    padding: "20px",
    borderWidth: 2,
    borderRadius: 2,
    borderColor: "gray",
    borderStyle: "dashed",
    backgroundColor: "#fafafa",
    color: "#bdbdbd",
    outline: "none",
    transition: "border .24s ease-in-out",
    cursor: "pointer"
};

const focusedStyle = {
    borderColor: "#3c3180"
};

const acceptStyle = {
    borderColor: "black"
};

const rejectStyle = {
    borderColor: "#ff1744"
};
export function Component(): JSX.Element {
    const barRef = useRef<HTMLDivElement>(null);
    const [uploadedFiles, setUploadedFiles] = useState<any[]>([]);
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [filesUploaded, setFilesUploaded] = useState<boolean>(false);
    const [filesProcessed, setFilesProcessed] = useState<boolean>(false);
    const [filesProcessing, setFilesProcessing] = useState<boolean>(false);
    const [error, setError] = useState<unknown>();

    const { getRootProps, getInputProps, isFocused, isDragAccept, isDragReject } = useDropzone({
        onDrop: acceptedFiles => {
            setUploadedFiles(acceptedFiles);
            const formData = new FormData();
            acceptedFiles.forEach((file: any) => {
                formData.append("file", file);
            });
            // make api request
            makeApiRequest(formData);
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

    const makeApiRequest = async (files: any) => {
        error && setError(undefined);
        setIsLoading(true);
        setFilesUploaded(false);

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
                            if (percentComplete < 86) {
                                barRef.current!.style.width = percentComplete + "%";
                            }
                        }
                    },
                    false
                );
                return xhr;
            },
            success: function (data) {
                if (data.success) {
                    setIsLoading(false);
                    setFilesUploaded(true);
                    setFilesProcessing(true);
                    barRef.current!.style.width = "100%";

                    const webSocket = new WebSocket(WEBSOCKET_ENDPOINT);

                    webSocket.onopen = function (event) {
                        console.log("WebSocket connection opened");
                    };

                    webSocket.onmessage = function (evt) {
                        var received_msg = JSON.parse(evt.data);
                        barRef.current!.style.width = `${received_msg.progress}%`;
                        if (received_msg.progress == 100) {
                            setFilesProcessed(true);
                            setFilesProcessing(false);
                        }
                    };

                    webSocket.onclose = function (event) {
                        console.log("WebSocket connection closed");
                    };
                } else {
                    setIsLoading(false);
                    setFilesUploaded(false);
                    setFilesProcessing(false);
                    setFilesProcessed(false);
                    setError("Something went wrong");
                }
            },
            error: function (e) {
                console.error(e);
                setIsLoading(false);
                setFilesUploaded(false);
                setFilesProcessing(false);
                setFilesProcessed(false);
                setError(e);
            }
        });
    };

    const handleFilesSubmit = (e: any) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        makeApiRequest(formData);
    };

    return (
        <div className={styles.uploadContainer}>
            <form method="POST" encType="multipart/form-data">
                {/* <FileUploader classes="file-uploader" name="file" types={fileTypes} multiple /> */}
                <div className={styles.uploadFiles} {...getRootProps({ style })}>
                    <input {...getInputProps()} name="file" />
                    <p>Drag and drop files here or click to browse.</p>
                    <em>(Only *.pdf files will be accepted)</em>
                    <ul>
                        {uploadedFiles!.map(file => (
                            <li key={file.name}>{file.name}</li>
                        ))}
                    </ul>
                    {isLoading ? <p>Uploading...</p> : null}
                    {filesUploaded ? <p>Files uploaded!</p> : null}
                    {error ? <p>Something went wrong!</p> : null}
                    {filesProcessed ? <p>Files processed!</p> : null}
                    {filesProcessing ? <p>Files processing...</p> : null}
                    {isLoading || filesUploaded || filesProcessing || filesProcessed ? (
                        <div className={styles.uploadProgress}>
                            <div className={styles.uploadBar} ref={barRef}></div>
                        </div>
                    ) : null}
                </div>
            </form>
        </div>
    );
}

Component.displayName = "Upload";
