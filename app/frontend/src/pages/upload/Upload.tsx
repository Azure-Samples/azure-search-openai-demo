import { ChangeEvent, useState } from "react";
import { uploadDocument } from "../../api";

const Upload = () => {
    const [selectedFiles, setSelectedFiles] = useState<File[]>([]);

    const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
        if (e.target.files) {
            setSelectedFiles(Array.from(e.target.files));
        }
    };

    const handleFileUpload = async () => {
        if (!selectedFiles || selectedFiles.length === 0) {
            alert("No files selected");
            return;
        }

        try {
            for (let i = 0; i < selectedFiles.length; i++) {
                const file = selectedFiles[i];
                await uploadDocument(file);
            }

            alert("All files uploaded successfully");
            setSelectedFiles([]); // Clear the selection
        } catch (err) {
            console.error(err);
            alert("There was an error uploading the files");
        }
    };

    return (
        <>
            <div className="w-1/2">
                <label className="block mb-2 text-sm font-medium text-gray-900 dark:text-white" htmlFor="multiple_files">
                    Upload multiple files
                </label>
                <input
                    onChange={handleFileChange}
                    className="block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 focus:outline-none"
                    id="multiple_files"
                    type="file"
                    multiple
                />
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-300" id="file_input_help">
                    PDF, MP3, WAV format
                </p>
            </div>

            <div className="pt-3">
                <button
                    onClick={handleFileUpload}
                    type="button"
                    className=" text-white bg-blue-700 hover:bg-blue-800 focus:ring-4 focus:ring-blue-300 font-medium rounded-lg text-sm px-5 py-2.5 mr-2 mb-2 dark:bg-blue-600 dark:hover:bg-blue-700 focus:outline-none dark:focus:ring-blue-800"
                >
                    Upload
                </button>
            </div>
        </>
    );
};

export default Upload;
