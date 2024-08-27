import { Spinner, SpinnerSize, MessageBar, MessageBarType, Link, IconButton } from "@fluentui/react";
import { useTranslation } from "react-i18next";
import React, { useState, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import styles from "./MarkdownViewer.module.css";

interface MarkdownViewerProps {
    src: string;
}

export const MarkdownViewer: React.FC<MarkdownViewerProps> = ({ src }) => {
    const [content, setContent] = useState<string>("");
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [error, setError] = useState<Error | null>(null);
    const { t } = useTranslation();

    /**
     * Anchor links result in HTTP 404 errors as the URL they point to does not exist.
     * This function removes them from the markdown.
     */
    const removeAnchorLinks = (markdown: string) => {
        const ancorLinksRegex = /\[.*?\]\(#.*?\)/g;
        return markdown.replace(ancorLinksRegex, "");
    };

    useEffect(() => {
        const fetchMarkdown = async () => {
            try {
                const response = await fetch(src);

                if (!response.ok) {
                    throw new Error("Failed loading markdown file.");
                }

                let markdownText = await response.text();
                markdownText = removeAnchorLinks(markdownText);
                setContent(markdownText);
            } catch (error: any) {
                setError(error);
            } finally {
                setIsLoading(false);
            }
        };

        fetchMarkdown();
    }, [src]);

    return (
        <div>
            {isLoading ? (
                <div className={`${styles.loading} ${styles.markdownViewer}`}>
                    <Spinner size={SpinnerSize.large} label="Loading file" />
                </div>
            ) : error ? (
                <div className={`${styles.error} ${styles.markdownViewer}`}>
                    <MessageBar messageBarType={MessageBarType.error} isMultiline={false}>
                        {error.message}
                        <Link href={src} download>
                            Download the file
                        </Link>
                    </MessageBar>
                </div>
            ) : (
                <div>
                    <IconButton
                        className={styles.downloadButton}
                        style={{ color: "black" }}
                        iconProps={{ iconName: "Save" }}
                        title={t("tooltips.save")}
                        ariaLabel={t("tooltips.save")}
                        href={src}
                        download
                    />
                    <ReactMarkdown children={content} remarkPlugins={[remarkGfm]} className={`${styles.markdown} ${styles.markdownViewer}`} />
                </div>
            )}
        </div>
    );
};
