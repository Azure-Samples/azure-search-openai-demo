import { Routes, Route, useNavigate, Navigate, Outlet } from "react-router-dom";
import { Link, LinkGroup, NavigationPanel } from "../../components/NavigationPanel";

import styles from "./Sources.module.css";
import { lazy } from "react";

const Sources = lazy(() => import("../../components/Sources/Sources"));
const SourcesFiles = lazy(() => import("../../components/Sources/SourcesFiles"));
const SourcesText = lazy(() => import("../../components/Sources/SourcesText"));
const SourcesWebsite = lazy(() => import("../../components/Sources/SourcesWebsite"));

export default function Component(): JSX.Element {
    const navigate = useNavigate();

    const handleNavClick = (link: Link) => {
        navigate(link.url);
    };

    const navLinks: LinkGroup[] = [
        {
            name: "Sources",
            links: [
                {
                    key: "files",
                    name: "Files",
                    url: "/sources/files"
                },
                {
                    key: "text",
                    name: "Text",
                    url: "/sources/text"
                },
                {
                    key: "website",
                    name: "Website",
                    url: "/sources/website"
                }
            ]
        }
    ];

    return (
        <div className={styles.container}>
            <div className={styles.sourcesContainer}>
                <div className={styles.navigationPanel}>
                    <NavigationPanel title="Sources" linkGroups={navLinks} onNavLinkClicked={handleNavClick} />
                </div>

                <div className={styles.outletContainer}>
                    <Routes>
                        <Route path="*" element={<Sources />}>
                            <Route path="files" element={<SourcesFiles />} />
                            <Route path="text" element={<SourcesText />} />
                            <Route path="website" element={<SourcesWebsite />} />
                        </Route>
                        <Route path="*" element={<Navigate to="/sources" replace />} />
                    </Routes>
                </div>
            </div>
        </div>
    );
}

Component.displayName = "Sources";
