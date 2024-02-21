import styles from "./UploadFiles.module.css";

import { Callout, IIconProps, IconButton, Label, PrimaryButton, Text } from "@fluentui/react";
import { ArrowUpload24Filled } from "@fluentui/react-icons";
import { useState, ChangeEvent, FormEvent } from "react";
import { IUploadResponse, uploadFileApi } from "../../api";
import { Button, Tooltip } from "@fluentui/react-components";

const UploadFiles = () => {
    const [isCalloutVisible, setIsCalloutVisible] = useState<boolean>(false);
    const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
    const [uploadedFile, setUploadedFile] = useState<IUploadResponse>();
    const [isLoading, setIsLoading] = useState<boolean>(false);

    const handleClick = () => {
        setIsCalloutVisible(!isCalloutVisible);
    };

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

    const handleRemoveFile = (fileToRemove: File) => {
        setSelectedFiles(prevFiles => prevFiles.filter(file => file !== fileToRemove));
    };

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
            const response: IUploadResponse = await uploadFileApi(request, undefined);
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
        <div className={`${styles.container}`}>
            <div>
                <Tooltip content="Upload Document" relationship="label">
                    <div>
                        <Button size="large" id="calloutButton" icon={<ArrowUpload24Filled primaryFill="rgba(115, 118, 225, 1)" />} onClick={handleClick} />
                    </div>
                </Tooltip>

                {isCalloutVisible && (
                    <Callout
                        role="dialog"
                        gapSpace={0}
                        className={styles.callout}
                        target="#calloutButton"
                        onDismiss={() => setIsCalloutVisible(false)}
                        setInitialFocus
                        directionalHint={5}
                    >
                        <form onSubmit={handleUploadFile} encType="multipart/form-data">
                            {/* Show the file input only if no files are selected */}
                            {selectedFiles.length === 0 && (
                                <div className={styles.selectContainer}>
                                    <PrimaryButton className={styles.submit}>
                                        Choose files
                                        <input accept=".pdf" className={styles.chooseFiles} type="file" multiple onChange={handleFileChange} />
                                    </PrimaryButton>
                                    <Text className={styles.info}>Only PDF is supported.</Text>
                                </div>
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
                            {isLoading && <div className={styles.padding8}>{"uploading files..."}</div>}
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
export default UploadFiles;
