import React, { useState, useEffect } from "react";
import { marked } from "marked";
import styles from "./MarkdownViewer.module.css";
import { Spinner, SpinnerSize, MessageBar, MessageBarType, Link, IconButton } from "@fluentui/react";

interface MarkdownViewerProps {
    src: string;
}

export const MarkdownViewer: React.FC<MarkdownViewerProps> = ({ src }) => {
    const [content, setContent] = useState<string>("");
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [error, setError] = useState<Error | null>(null);

    /**
     * Anchor links are not handled well by 'marked' and result in HTTP 404 errors as the URL they point to does not exist.
     * This function removes them from the resulted HTML.
     */
    const removeAnchorLinks = (html: string) => {
        const ancorLinksRegex = /<a\s+(?:[^>]*?\s+)?href=['"](#[^"']*?)['"][^>]*?>/g;
        return html.replace(ancorLinksRegex, "");
    };

    useEffect(() => {
        const fetchMarkdown = async () => {
            try {
                const response = await fetch(src);

                if (!response.ok) {
                    throw new Error("Failed loading markdown file.");
                }

                const markdownText = await response.text();
                const parsedHtml = await marked.parse(markdownText);
                const cleanedHtml = removeAnchorLinks(parsedHtml);
                setContent(cleanedHtml);
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
                        title="Save"
                        ariaLabel="Save"
                        href={src}
                        download
                    />
                    <div className={`${styles.markdown} ${styles.markdownViewer}`} dangerouslySetInnerHTML={{ __html: content }} />
                </div>
            )}
        </div>
    );
};
