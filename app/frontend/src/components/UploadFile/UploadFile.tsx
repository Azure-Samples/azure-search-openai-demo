import React, { useState, ChangeEvent, FormEvent } from "react";
import styles from "./UploadFile.module.css";
import { IIconProps, Callout, ActionButton, PrimaryButton, Label, IconButton, Text } from "@fluentui/react";
import { FileUploadResponse, uploadFileApi } from "../../api";
import { useMsal } from "@azure/msal-react";
import { useLogin, getToken } from "../../authConfig";

interface Props {
    className?: string;
}

export const UploadFile: React.FC<Props> = ({ className }: Props) => {
    // State variables to manage the component behavior
    const [isCalloutVisible, setIsCalloutVisible] = useState<boolean>(false);
    const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [uploadedFile, setUploadedFile] = useState<FileUploadResponse>();

    if (!useLogin) {
        console.error("This component requires useLogin to be true");
        return null;
    }

    const client = useMsal().instance;

    // Handler for the "Upload Files" button click
    const handleButtonClick = () => {
        setIsCalloutVisible(!isCalloutVisible); // Toggle the Callout visibility
    };

    // Handler for file input change event
    const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
        const selectedFileList: File[] = [];
        if (e.target.files) {
            // Extract the selected files and store them in the state
            for (let i = 0; i < e.target.files.length; i++) {
                selectedFileList.push(e.target.files.item(i)!);
            }
        }
        setSelectedFiles(selectedFileList);
    };

    // Handler for removing a selected file from the list
    const handleRemoveFile = (fileToRemove: File) => {
        const filteredFiles = selectedFiles.filter(file => file !== fileToRemove);
        setSelectedFiles(filteredFiles);
    };

    // Handler for the form submission (file upload)
    const handleUploadFile = async (ev: FormEvent) => {
        ev.preventDefault();
        setIsLoading(true); // Start the loading state
        const formData = new FormData();
        // Append each file to the FormData
        selectedFiles.forEach((file, index) => {
            formData.append(`files`, file);
        });

        try {
            const request: FormData = formData;
            const idToken = await getToken(client);
            if (!idToken) {
                throw new Error("No authentication token available");
            }
            const response: FileUploadResponse = await uploadFileApi(request, idToken);
            setUploadedFile(response);
            setIsLoading(false);
        } catch (error) {
            setIsLoading(false);
        }

        setSelectedFiles([]);
    };

    const addIcon: IIconProps = { iconName: "Add" };
    const Remove: IIconProps = { iconName: "delete" };

    return (
        <div className={`${styles.container} ${className ?? ""}`}>
            <div>
                <ActionButton className={styles.btn_action} id="calloutButton" iconProps={addIcon} allowDisabledFocus onClick={handleButtonClick}>
                    Upload File
                </ActionButton>

                {isCalloutVisible && (
                    <Callout
                        role="dialog"
                        gapSpace={0}
                        className={styles.callout}
                        target="#calloutButton"
                        onDismiss={() => setIsCalloutVisible(false)}
                        setInitialFocus
                    >
                        <form onSubmit={handleUploadFile} encType="multipart/form-data">
                            {/* Show the file input only if no files are selected */}
                            {selectedFiles.length === 0 && (
                                <>
                                    <div className={styles.btn}>
                                        <Label>Choose file</Label>
                                        <input accept=".pdf" className={styles.chooseFiles} type="file" multiple onChange={handleFileChange} />
                                    </div>
                                </>
                            )}

                            {/* Show the upload button and the number of selected files if files are selected */}
                            {selectedFiles.length > 0 && (
                                <div className={styles.SubmitContainer}>
                                    <Label>Selected Files ({selectedFiles.length})</Label>
                                    <PrimaryButton className={styles.submit} type="submit">
                                        Submit
                                    </PrimaryButton>
                                </div>
                            )}

                            {/* Show a loading message while files are being uploaded */}
                            {isLoading && <div className={styles.padding8}>{"Uploading files..."}</div>}
                            {uploadedFile && <div className={styles.padding8}>{uploadedFile.message}</div>}
                            {/* Display the list of selected files */}

                            {selectedFiles.map((item, index) => {
                                return (
                                    <div key={index} className={styles.list}>
                                        <div className={styles.item}>{item.name}</div>
                                        {/* Button to remove a file from the list */}
                                        <IconButton
                                            className={styles.delete}
                                            onClick={() => handleRemoveFile(item)}
                                            iconProps={Remove}
                                            title="Remove file"
                                            ariaLabel="Remove file"
                                        />
                                    </div>
                                );
                            })}
                        </form>
                    </Callout>
                )}
            </div>
        </div>
    );
};
