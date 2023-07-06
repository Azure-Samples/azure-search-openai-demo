import { ChangeEvent, useEffect, useRef, useState } from "react";
import { BlobDocument, deleteDocument, getDocumentNames } from "../../api";
import Pagination from "../../components/Pagination/Pagination";

enum ActionOption {
    // Activate = "activate",
    // Deactivate = "deactivate",
    Delete = "delete"
}

export interface TableData {
    id: number;
    name: string;
    // status: string;
    dateUploaded: string;
    // size: string;
}

const KnowledgeBase = () => {
    const [isActionDropdownOpen, setActionDropdownOpen] = useState(false);
    const [selectedAction, setSelectedAction] = useState("");
    const [selectedAll, setSelectedAll] = useState(false);
    const [selectedItems, setSelectedItems] = useState<number[]>([]);
    const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc");
    const [sortedColumn, setSortedColumn] = useState<keyof TableData>("name");
    const [searchQuery, setSearchQuery] = useState("");
    const [currentPage, setCurrentPage] = useState(1);

    const [deleteError, setDeleteError] = useState<unknown>();
    const [deleteLoading, setDeleteLoading] = useState<boolean>(false);

    const [error, setError] = useState<unknown>();
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [tableData, setTableData] = useState<TableData[]>([]);
    const [filteredData, setFilteredData] = useState<TableData[]>([]);
    const [currentItems, setCurrentItems] = useState<TableData[]>([]);

    const itemsPerPage = 10;
    const dropdownRef = useRef<HTMLDivElement>(null);

    const getTableData = async () => {
        error && setError(undefined);
        setIsLoading(true);

        try {
            const result = await getDocumentNames();

            const formattedResult = result.map((item, index) => {
                console.log("item in first loop");
                console.log(item);
                return {
                    id: index + 1, // Generate IDs starting from 1
                    name: item[0],
                    dateUploaded: new Date(item[1][0]).toLocaleString() // Convert blob's last_modified date to string format
                    // status and size fields are not filled because they are not available in your current backend function
                };
            });
            console.log(formattedResult);
            setTableData(formattedResult);
        } catch (e) {
            setError(e);
        } finally {
            setIsLoading(false);
        }
    };

    const deleteDocuments = async (documentNames: string[]) => {
        deleteError && setDeleteError(undefined);
        setDeleteLoading(true);

        try {
            for (const blobName of documentNames) {
                const result = await deleteDocument(blobName);
                console.log(`Result for ${blobName}: ${result}`); // Log the server's response to deleting each blob
            }

            // After successful deletion, refresh the table data
            await getTableData();
        } catch (e) {
            setDeleteError(e);
        } finally {
            setDeleteError(false);
        }
    };

    const toggleActionDropdown = () => {
        console.log("selectedItems");
        console.log(selectedItems);
        console.log("currentItems");
        console.log(currentItems);
        setActionDropdownOpen(!isActionDropdownOpen);
    };

    const handleOutsideClick = (event: MouseEvent) => {
        if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
            setActionDropdownOpen(false);
        }
    };

    const handleActionClick = async (option: ActionOption) => {
        setSelectedAction(option);
        console.log("selectedItems");
        console.log(selectedItems);
        if (option == ActionOption.Delete) {
            for (const item of selectedItems) {
                await deleteDocuments([currentItems[item - 1].name]);
            }
        }
        setActionDropdownOpen(false);
    };

    const handleSelectAllClick = (e: React.ChangeEvent<HTMLInputElement>) => {
        const checked = e.target.checked;
        setSelectedAll(checked);
        setSelectedItems(checked ? tableData.map(item => item.id) : []);
    };

    const handleItemSelected = (e: React.ChangeEvent<HTMLInputElement>, itemId: number) => {
        const checked = e.target.checked;

        if (checked) {
            setSelectedItems(prevSelectedItems => [...prevSelectedItems, itemId]);
        } else {
            setSelectedItems(prevSelectedItems => prevSelectedItems.filter(item => item !== itemId));
        }
    };

    const isItemSelected = (itemId: number) => selectedItems.includes(itemId);

    const handleSort = (column: keyof TableData) => {
        setSortOrder(prevSortOrder => (prevSortOrder === "asc" ? "desc" : "asc"));
        setSortedColumn(column);
    };

    const getSortArrow = (column: keyof TableData) => {
        if (column === sortedColumn) {
            return sortOrder === "asc" ? (
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" className="bi pl-1 bi-chevron-up" viewBox="0 0 16 16">
                    <path fill-rule="evenodd" d="M7.646 4.646a.5.5 0 0 1 .708 0l6 6a.5.5 0 0 1-.708.708L8 5.707l-5.646 5.647a.5.5 0 0 1-.708-.708l6-6z" />
                </svg>
            ) : (
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" className="bi pl-1 bi-chevron-down" viewBox="0 0 16 16">
                    <path
                        fill-rule="evenodd"
                        d="M1.646 4.646a.5.5 0 0 1 .708 0L8 10.293l5.646-5.647a.5.5 0 0 1 .708.708l-6 6a.5.5 0 0 1-.708 0l-6-6a.5.5 0 0 1 0-.708z"
                    />
                </svg>
            );
        }
        return null;
    };

    const handleSearch = (e: ChangeEvent<HTMLInputElement>) => {
        setSearchQuery(e.target.value);
    };

    useEffect(() => {
        getTableData();
        document.addEventListener("mousedown", handleOutsideClick);
        return () => {
            document.removeEventListener("mousedown", handleOutsideClick);
        };
    }, []);

    useEffect(() => {
        console.log("ran second useEffect");
        const filteredData = tableData.filter(item => item.name.toLowerCase().includes(searchQuery.toLowerCase()));
        setFilteredData(filteredData);

        const sortedData = [...filteredData].sort((a, b) => {
            const columnA = a[sortedColumn];
            const columnB = b[sortedColumn];

            if (columnA < columnB) {
                return sortOrder === "asc" ? -1 : 1;
            }
            if (columnA > columnB) {
                return sortOrder === "asc" ? 1 : -1;
            }
            return 0;
        });

        const indexOfLastItem = Math.min(currentPage * itemsPerPage, filteredData.length);
        const indexOfFirstItem = Math.max((currentPage - 1) * itemsPerPage, 0);

        const currentItems = sortedData.slice(indexOfFirstItem, indexOfLastItem);
        setCurrentItems(currentItems);
    }, [tableData, searchQuery, sortedColumn, sortOrder, currentPage]);

    if (isLoading) {
        return <h1>is loading</h1>;
    }

    return (
        <div>
            <div className="relative overflow-x-auto sm:rounded-lg">
                <div className="flex items-center justify-between pb-4 bg-white">
                    {/* Dropdown Button */}
                    <div className="pb-5 pt-5 pl-2">
                        <button
                            className={`inline-flex items-center text-gray-500 bg-white border border-gray-300 focus:outline-none hover:bg-gray-100 focus:ring-4 focus:ring-gray-200 font-medium rounded-lg text-sm px-3 py-1.5 disabled:opacity-60`}
                            type="button"
                            onClick={toggleActionDropdown}
                            disabled={selectedItems.length === 0}
                        >
                            Bulk Action
                            <svg
                                className="w-3 h-3 ml-2"
                                aria-hidden="true"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                                xmlns="http://www.w3.org/2000/svg"
                            >
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                            </svg>
                        </button>
                        {isActionDropdownOpen && (
                            <div ref={dropdownRef} id="dropdownAction" className="z-10 absolute bg-white divide-y divide-gray-100 rounded-lg shadow w-44">
                                <ul className="py-1 text-sm text-gray-700" aria-labelledby="dropdownActionButton">
                                    <li>
                                        <a href="#" className="block px-4 py-2 hover:bg-gray-100" onClick={() => handleActionClick(ActionOption.Delete)}>
                                            Delete
                                        </a>
                                    </li>
                                </ul>
                            </div>
                        )}
                    </div>

                    {/* Search */}
                    <div className="relative">
                        <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
                            <svg
                                className="w-5 h-5 text-gray-500 dark:text-gray-400"
                                aria-hidden="true"
                                fill="currentColor"
                                viewBox="0 0 20 20"
                                xmlns="http://www.w3.org/2000/svg"
                            >
                                <path
                                    fill-rule="evenodd"
                                    d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z"
                                    clip-rule="evenodd"
                                ></path>
                            </svg>
                        </div>
                        <input
                            type="text"
                            id="table-search-users"
                            onChange={handleSearch}
                            value={searchQuery}
                            className="block p-2 pl-10 text-sm text-gray-900 border border-gray-300 rounded-lg w-80 bg-gray-50 focus:ring-blue-500 focus:border-blue-500"
                            placeholder="Search for documents"
                        />
                    </div>
                </div>

                <table className="w-full text-sm text-left text-gray-500">
                    <thead className="text-xs text-gray-700 uppercase bg-gray-50">
                        <tr>
                            <th scope="col" className="p-4">
                                <div className="flex items-center">
                                    <input
                                        id="checkbox-all-search"
                                        type="checkbox"
                                        checked={selectedAll}
                                        onChange={handleSelectAllClick}
                                        className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 focus:ring-2 "
                                    />
                                </div>
                            </th>
                            <th scope="col" className="px-6 py-3 w-1/5" onClick={() => handleSort("name")}>
                                <button className="flex items-center items-center text-left focus:outline-none">
                                    Name
                                    {getSortArrow("name")}
                                </button>
                            </th>
                            {/* <th scope="col" className="px-6 py-3 w-1/5" onClick={() => handleSort("status")}>
                                <button className="flex items-center text-left focus:outline-none">
                                    Status
                                    {getSortArrow("status")}
                                </button>
                            </th> */}
                            <th scope="col" className="px-6 py-3 w-1/5" onClick={() => handleSort("dateUploaded")}>
                                <button className="flex items-center text-left focus:outline-none">
                                    Date Uploaded
                                    {getSortArrow("dateUploaded")}
                                </button>
                            </th>
                            {/* <th scope="col" className="px-6 py-3 w-1/5" onClick={() => handleSort("size")}>
                                <button className="flex items-center text-left focus:outline-none">
                                    Size
                                    {getSortArrow("size")}
                                </button>
                            </th> */}
                            <th scope="col" className="px-6 py-3">
                                Action
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        {currentItems.map(item => (
                            <tr key={item.id} className="bg-white border-b hover:bg-gray-50">
                                <td className="w-4 p-4">
                                    <div className="flex items-center">
                                        <input
                                            id="checkbox-table-search-1"
                                            type="checkbox"
                                            checked={isItemSelected(item.id)}
                                            onChange={e => handleItemSelected(e, item.id)}
                                            className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 focus:ring-2 "
                                        />
                                    </div>
                                </td>
                                <th scope="row" className="px-6 py-4 font-medium text-gray-900 whitespace-nowrap">
                                    {item.name}
                                </th>
                                {/* <td className="px-6 py-4">{item.status}</td> */}
                                <td className="px-6 py-4">{item.dateUploaded}</td>
                                {/* <td className="px-6 py-4">{item.size}</td> */}
                                <td className="px-6 py-4">
                                    <button>
                                        <a
                                            onClick={() => {
                                                deleteDocuments([item.name]);
                                            }}
                                            className="font-medium text-blue-600 hover:underline"
                                        >
                                            Delete
                                        </a>
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            <Pagination filteredData={filteredData} itemsPerPage={itemsPerPage} setCurrentPage={setCurrentPage} currentPage={currentPage} />
        </div>
    );
};

export default KnowledgeBase;
