import React from "react";
import ReactDOM from "react-dom/client";
import { createHashRouter, RouterProvider } from "react-router-dom";
import { initializeIcons } from "@fluentui/react";

import "./index.css";

import Layout from "./pages/layout/Layout";
import Chat from "./pages/chat/Chat";
import KnowledgeBase from "./pages/knowledgeBase/KnowledgeBase";
import Upload from "./pages/upload/Upload";
initializeIcons();

export default function App() {
    return (
        <HashRouter>
            <Routes>
                <Route path="/" element={<Layout />}>
                    <Route index element={<Chat />} />
                    <Route path="qa" element={<OneShot />} />
                    <Route path="knowledge-base" element={<KnowledgeBase />} />
                    <Route path="upload" element={<Upload />} />
                    <Route path="*" element={<NoPage />} />
                </Route>
            </Routes>
        </HashRouter>
    );
}
// const router = createHashRouter([
//     {
//         path: "/",
//         element: <Layout />,
//         children: [
//             {
//                 index: true,
//                 element: <Chat />
//             },
//             {
//                 path: "qa",
//                 lazy: () => import("./pages/oneshot/OneShot")
//             },
//             {
//                 path: "*",
//                 lazy: () => import("./pages/NoPage")
//             }
//         ]
//     }
// ]);

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
    <React.StrictMode>
        <RouterProvider router={router} />
    </React.StrictMode>
);
