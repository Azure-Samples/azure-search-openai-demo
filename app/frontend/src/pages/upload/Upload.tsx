"use client";

import { ChangeEvent, useState } from "react";
import { uploadDocument } from "../../api";
import { Modal, ModalInterface, ModalOptions } from "flowbite";

const Upload = () => {
    const $modalElement: HTMLElement | null = document.querySelector("#defaultModal");

    const modalOptions: ModalOptions = {
        placement: "bottom-right",
        backdrop: "dynamic",
        backdropClasses: "bg-gray-900 bg-opacity-50 fixed inset-0 z-40",
        closable: true,
        onHide: () => {
            console.log("modal is hidden");
        },
        onShow: () => {
            console.log("modal is shown");
        },
        onToggle: () => {
            console.log("modal has been toggled");
        }
    };

    const modal: ModalInterface = new Modal($modalElement, modalOptions);

    const [selectedFiles, setSelectedFiles] = useState<File[]>([]);

    const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
        if (e.target.files) {
            setSelectedFiles(Array.from(e.target.files));
        }
    };

    const handleFileUpload = async () => {
        // if (!selectedFiles || selectedFiles.length === 0) {
        //     alert("No files selected");
        //     return;
        // }

        console.log(selectedFiles);
        modal.show();
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
                <label className="block mb-2 text-sm font-medium text-gray-900" htmlFor="multiple_files">
                    Upload multiple files
                </label>
                <input
                    onChange={handleFileChange}
                    className="block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 focus:outline-none"
                    id="multiple_files"
                    type="file"
                    multiple
                />
                <p className="mt-1 text-sm text-gray-500" id="file_input_help">
                    PDF, MP3, WAV format
                </p>
            </div>

            <div className="pt-3">
                <button
                    onClick={handleFileUpload}
                    data-modal-target="defaultModal"
                    data-modal-toggle="defaultModal"
                    type="button"
                    className=" text-white bg-blue-700 hover:bg-blue-800 focus:ring-4 focus:ring-blue-300 font-medium rounded-lg text-sm px-5 py-2.5 mr-2 mb-2"
                >
                    Upload
                </button>
            </div>

            <div
                id="defaultModal"
                // tabIndex="-1"
                data-modal-backdrop="static"
                aria-hidden="true"
                className="fixed top-0 left-0 right-0 z-50 hidden w-full p-4 overflow-x-hidden overflow-y-auto md:inset-0 h-[calc(100%-1rem)] max-h-full"
            >
                <div className="relative w-full max-w-2xl max-h-full">
                    <div className="relative bg-white rounded-lg shadow">
                        <div className="flex items-start justify-between p-4 border-b rounded-t">
                            <h3 className="text-xl font-semibold text-gray-900">Upload Files</h3>
                            <button
                                type="button"
                                className="text-gray-400 bg-transparent hover:bg-gray-200 hover:text-gray-900 rounded-lg text-sm w-8 h-8 ml-auto inline-flex justify-center items-center"
                                data-modal-hide="defaultModal"
                            >
                                <svg className="w-3 h-3" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 14 14">
                                    <path
                                        stroke="currentColor"
                                        stroke-linecap="round"
                                        stroke-linejoin="round"
                                        stroke-width="2"
                                        d="m1 1 6 6m0 0 6 6M7 7l6-6M7 7l-6 6"
                                    />
                                </svg>
                                <span className="sr-only">Close modal</span>
                            </button>
                        </div>
                        <div className="p-6 space-y-6">
                            <div className="relative overflow-x-auto">
                                <table className="w-full text-sm text-left text-gray-500 dark:text-gray-400">
                                    <thead className="text-xs text-gray-700 uppercase dark:bg-gray-700 dark:text-gray-400">
                                        <tr>
                                            <th scope="col" className="px-6 py-3">
                                                File name
                                            </th>
                                            <th scope="col" className="px-6 py-3">
                                                Status
                                            </th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {selectedFiles.map((file, index) => (
                                            <tr key={index} className="bg-white border-b dark:bg-gray-800">
                                                <th scope="row" className="px-6 py-4 font-medium text-gray-900 whitespace-normal ">
                                                    {file.name}
                                                </th>
                                                <td className="px-6 py-4">
                                                    <span className="bg-green-100 text-green-800 text-xs font-medium mr-2 px-2.5 py-0.5 rounded">Uploaded</span>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                        <div className="flex items-center p-6 space-x-2 border-t border-gray-200 rounded-b ">
                            <button
                                data-modal-hide="defaultModal"
                                type="button"
                                className="text-white bg-blue-700 hover:bg-blue-800 focus:ring-4 focus:outline-none focus:ring-blue-300 font-medium rounded-lg text-sm px-5 py-2.5 text-center"
                            >
                                Done
                            </button>
                            <button
                                data-modal-hide="defaultModal"
                                type="button"
                                className="text-gray-500 bg-white hover:bg-gray-100 focus:ring-4 focus:outline-none focus:ring-blue-300 rounded-lg border border-gray-200 text-sm font-medium px-5 py-2.5 hover:text-gray-900 focus:z-10 "
                            >
                                Cancel
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </>
    );
};

export default Upload;
