import { Dispatch, SetStateAction } from "react";
import { TableData } from "../../pages/knowledgeBase/KnowledgeBase";

interface PaginationProps {
    filteredData: TableData[];
    itemsPerPage: number;
    currentPage: number;
    setCurrentPage: Dispatch<SetStateAction<number>>;
}

const Pagination: React.FC<PaginationProps> = ({ filteredData, itemsPerPage, currentPage, setCurrentPage }) => {
    // Pagination Logic
    const totalPages = Math.ceil(filteredData.length / itemsPerPage);

    const indexOfLastItem = Math.min(currentPage * itemsPerPage, filteredData.length);

    const indexOfFirstItem = Math.max((currentPage - 1) * itemsPerPage, 0);

    // Handler for changing the current page
    const handlePageChange = (page: number) => {
        if (page) setCurrentPage(page);
    };

    const Ellipsis = () => {
        return (
            <li>
                <a className="px-3 py-2 leading-tight text-gray-500 bg-white border border-gray-300 hover:bg-gray-100 hover:text-gray-700 ">...</a>
            </li>
        );
    };

    return (
        <nav className="flex items-center justify-between pt-4" aria-label="Table navigation">
            <span className="text-sm font-normal text-gray-500">
                {"Showing "}
                <span className="font-semibold text-gray-900">
                    {indexOfFirstItem + 1}-{Math.min(indexOfLastItem, filteredData.length)}
                </span>{" "}
                of <span className="font-semibold text-gray-900">{filteredData.length}</span> Documents
            </span>

            <ul className="inline-flex items-center -space-x-px">
                <li>
                    <button
                        className={`block px-3 py-2 ml-0 leading-tight text-gray-500 bg-white border border-gray-300 rounded-l-lg hover:bg-gray-100 hover:text-gray-700
              ${
                  currentPage === 1
                      ? "text-gray-400 cursor-not-allowed bg-white border border-gray-300 rounded-l-lg"
                      : "text-gray-500 bg-white border border-gray-300 rounded-l-lg hover:bg-gray-100 hover:text-gray-700"
              }`}
                        onClick={() => handlePageChange(currentPage - 1)}
                        disabled={currentPage === 1}
                    >
                        <span className="sr-only">Previous</span>
                        <svg className="w-5 h-5" aria-hidden="true" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
                            <path
                                fill-rule="evenodd"
                                d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z"
                                clip-rule="evenodd"
                            ></path>
                        </svg>
                    </button>
                </li>

                {/* Base Case: Less than 5 pages */}
                {totalPages <= 5 &&
                    Array.from({ length: totalPages }, (_, index) => index + 1).map(page => (
                        <li key={page}>
                            <button onClick={() => handlePageChange(page)}>
                                <a
                                    className={`px-3 py-2 leading-tight ${
                                        page === currentPage
                                            ? "text-blue-600 border border-blue-300 bg-blue-50 hover:bg-blue-100 hover:text-blue-700"
                                            : "text-gray-500 bg-white border border-gray-300 hover:bg-gray-100 hover:text-gray-700"
                                    }`}
                                >
                                    {page}
                                </a>
                            </button>
                        </li>
                    ))}

                {/* In the middle of pagination with ... on both sides */}
                {totalPages > 5 && currentPage > 4 && totalPages - currentPage > 3 && (
                    <>
                        <li>
                            <button onClick={() => handlePageChange(1)}>
                                <a className="px-3 py-2 leading-tight text-gray-500 bg-white border border-gray-300 hover:bg-gray-100 hover:text-gray-700">1</a>
                            </button>
                        </li>
                        <Ellipsis />
                        <li>
                            <button onClick={() => handlePageChange(currentPage - 1)}>
                                <a className="px-3 py-2 leading-tight text-gray-500 bg-white border border-gray-300 hover:bg-gray-100 hover:text-gray-700">
                                    {currentPage - 1}
                                </a>
                            </button>
                        </li>
                        <li>
                            <button onClick={() => handlePageChange(1)}>
                                <a className="px-3 py-2 leading-tight text-blue-600 border border-blue-300 bg-blue-50 hover:bg-blue-100 hover:text-blue-700">
                                    {currentPage}
                                </a>
                            </button>
                        </li>
                        <li>
                            <button onClick={() => handlePageChange(1)}>
                                <a className="px-3 py-2 leading-tight text-gray-500 bg-white border border-gray-300 hover:bg-gray-100 hover:text-gray-700">
                                    {currentPage + 1}
                                </a>
                            </button>
                        </li>
                        <Ellipsis />
                        <li>
                            <button onClick={() => handlePageChange(totalPages)}>
                                <a
                                    className={`px-3 py-2 leading-tight ${
                                        currentPage === totalPages
                                            ? "text-blue-600 border border-blue-300 bg-blue-50 hover:bg-blue-100 hover:text-blue-700"
                                            : "text-gray-500 bg-white border border-gray-300 hover:bg-gray-100 hover:text-gray-700"
                                    }`}
                                >
                                    {totalPages}
                                </a>
                            </button>
                        </li>
                    </>
                )}

                {/* Near the end of pagination with ... on the beginning */}
                {totalPages > 5 && totalPages - currentPage < 4 && (
                    <>
                        <li>
                            <button onClick={() => handlePageChange(1)}>
                                <a className="px-3 py-2 leading-tight text-gray-500 bg-white border border-gray-300 hover:bg-gray-100 hover:text-gray-700">1</a>
                            </button>
                        </li>
                        <Ellipsis />
                        <li>
                            <button onClick={() => handlePageChange(currentPage - 1)}>
                                <a
                                    className={`px-3 py-2 leading-tight ${
                                        totalPages - 4 === currentPage
                                            ? "text-blue-600 border border-blue-300 bg-blue-50 hover:bg-blue-100 hover:text-blue-700"
                                            : "text-gray-500 bg-white border border-gray-300 hover:bg-gray-100 hover:text-gray-700"
                                    }`}
                                >
                                    {totalPages - 4}
                                </a>
                            </button>
                        </li>
                        <li>
                            <button onClick={() => handlePageChange(currentPage - 1)}>
                                <a
                                    className={`px-3 py-2 leading-tight ${
                                        totalPages - 3 === currentPage
                                            ? "text-blue-600 border border-blue-300 bg-blue-50 hover:bg-blue-100 hover:text-blue-700"
                                            : "text-gray-500 bg-white border border-gray-300 hover:bg-gray-100 hover:text-gray-700"
                                    }`}
                                >
                                    {totalPages - 3}
                                </a>
                            </button>
                        </li>
                        <li>
                            <button onClick={() => handlePageChange(currentPage - 1)}>
                                <a
                                    className={`px-3 py-2 leading-tight ${
                                        totalPages - 2 === currentPage
                                            ? "text-blue-600 border border-blue-300 bg-blue-50 hover:bg-blue-100 hover:text-blue-700"
                                            : "text-gray-500 bg-white border border-gray-300 hover:bg-gray-100 hover:text-gray-700"
                                    }`}
                                >
                                    {totalPages - 2}
                                </a>
                            </button>
                        </li>
                        <li>
                            <button onClick={() => handlePageChange(currentPage - 1)}>
                                <a
                                    className={`px-3 py-2 leading-tight ${
                                        totalPages - 1 === currentPage
                                            ? "text-blue-600 border border-blue-300 bg-blue-50 hover:bg-blue-100 hover:text-blue-700"
                                            : "text-gray-500 bg-white border border-gray-300 hover:bg-gray-100 hover:text-gray-700"
                                    }`}
                                >
                                    {totalPages - 1}
                                </a>
                            </button>
                        </li>
                        <li>
                            <button onClick={() => handlePageChange(currentPage - 1)}>
                                <a
                                    className={`px-3 py-2 leading-tight ${
                                        totalPages === currentPage
                                            ? "text-blue-600 border border-blue-300 bg-blue-50 hover:bg-blue-100 hover:text-blue-700"
                                            : "text-gray-500 bg-white border border-gray-300 hover:bg-gray-100 hover:text-gray-700"
                                    }`}
                                >
                                    {totalPages}
                                </a>
                            </button>
                        </li>
                    </>
                )}

                {totalPages > 5 && currentPage < 5 && (
                    <>
                        {Array.from({ length: Math.min(totalPages, 5) }, (_, index) => index + 1).map(page => (
                            <li key={page}>
                                <button onClick={() => handlePageChange(page)}>
                                    <a
                                        className={`px-3 py-2 leading-tight ${
                                            page === currentPage
                                                ? "text-blue-600 border border-blue-300 bg-blue-50 hover:bg-blue-100 hover:text-blue-700"
                                                : "text-gray-500 bg-white border border-gray-300 hover:bg-gray-100 hover:text-gray-700"
                                        }`}
                                    >
                                        {page}
                                    </a>
                                </button>
                            </li>
                        ))}
                        <Ellipsis />
                        <li>
                            <button onClick={() => handlePageChange(totalPages)}>
                                <a
                                    className={`px-3 py-2 leading-tight ${
                                        currentPage === totalPages
                                            ? "text-blue-600 border border-blue-300 bg-blue-50 hover:bg-blue-100 hover:text-blue-700"
                                            : "text-gray-500 bg-white border border-gray-300 hover:bg-gray-100 hover:text-gray-700"
                                    }`}
                                >
                                    {totalPages}
                                </a>
                            </button>
                        </li>
                    </>
                )}

                <li>
                    <button
                        className={`block px-3 py-2 leading-tight text-gray-500 bg-white border border-gray-300 rounded-r-lg hover:bg-gray-100 hover:text-gray-700 ${
                            currentPage === totalPages
                                ? "text-gray-400 cursor-not-allowed bg-white border border-gray-300 rounded-r-lg"
                                : "text-gray-500 bg-white border border-gray-300 rounded-r-lg hover:bg-gray-100 hover:text-gray-700"
                        }`}
                        onClick={() => handlePageChange(currentPage + 1)}
                        disabled={currentPage === totalPages}
                    >
                        <span className="sr-only">Next</span>
                        <svg className="w-5 h-5" aria-hidden="true" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
                            <path
                                fillRule="evenodd"
                                d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
                                clipRule="evenodd"
                            ></path>
                        </svg>
                    </button>
                </li>
            </ul>
        </nav>
    );
};

export default Pagination;
