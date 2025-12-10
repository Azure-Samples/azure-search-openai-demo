import { Spinner, SpinnerSize, MessageBar, MessageBarType, Link, IconButton } from "@fluentui/react";
import { useTranslation } from "react-i18next";
import React, { useState, useEffect } from "react";
// @ts-ignore - postal-mime doesn't have type definitions
import PostalMime from "postal-mime";
import MsgReader from "@kenjiuno/msgreader";
import { useMsal } from "@azure/msal-react";
import { getHeaders } from "../../api";
import { useLogin, getToken } from "../../authConfig";

import styles from "./EmailViewer.module.css";

interface EmailViewerProps {
    src: string;
    height?: string;
}

interface ParsedEmail {
    subject?: string;
    from?: { name?: string; address?: string };
    to?: Array<{ name?: string; address?: string }>;
    cc?: Array<{ name?: string; address?: string }>;
    date?: string;
    html?: string;
    text?: string;
    attachments?: Array<{ filename?: string; size?: number }>;
}

export const EmailViewer: React.FC<EmailViewerProps> = ({ src, height }) => {
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [error, setError] = useState<Error | null>(null);
    const [emailHtml, setEmailHtml] = useState<string>("");
    const { t } = useTranslation();
    const client = useLogin ? useMsal().instance : undefined;

    // Helper function to escape HTML
    const escapeHtml = (text: string): string => {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    };

    // Helper function to format bytes
    const formatBytes = (bytes: number): string => {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    };

    // Parse MSG file
    const parseMsgFile = async (arrayBuffer: ArrayBuffer): Promise<ParsedEmail> => {
        try {
            const msgReader = new MsgReader(arrayBuffer);
            const fileData = msgReader.getFileData();
            
            console.log("MSG parsed successfully:", {
                subject: fileData.subject,
                senderName: fileData.senderName,
                hasBody: !!fileData.body,
                hasBodyHTML: !!fileData.bodyHtml
            });

            // Convert MSG recipients to standard format
            const to = fileData.recipients?.map(r => ({
                name: r.name || '',
                address: r.email || ''
            })) || [];

            return {
                subject: fileData.subject || '',
                from: {
                    name: fileData.senderName || '',
                    address: fileData.senderEmail || ''
                },
                to: to,
                cc: [], // MSG parser might not separate CC easily
                date: fileData.creationTime || fileData.messageDeliveryTime || '',
                html: fileData.bodyHtml || '',
                text: fileData.body || '',
                attachments: fileData.attachments?.map(att => {
                    const attachment = att as any;
                    return {
                        filename: att.fileName || att.name || 'unnamed',
                        size: attachment.content?.length || attachment.data?.length || attachment.size || 0
                    };
                }) || []
            };
        } catch (err) {
            console.error("Error parsing MSG file:", err);
            throw new Error(`Failed to parse MSG file: ${err instanceof Error ? err.message : 'Unknown error'}`);
        }
    };

    // Parse EML file
    const parseEmlFile = async (arrayBuffer: ArrayBuffer): Promise<ParsedEmail> => {
        try {
            const parser = new PostalMime();
            const email = await parser.parse(arrayBuffer);
            
            console.log("EML parsed successfully:", {
                subject: email.subject,
                from: email.from,
                hasHtml: !!email.html,
                hasText: !!email.text
            });

            return email as ParsedEmail;
        } catch (err) {
            console.error("Error parsing EML file:", err);
            throw new Error(`Failed to parse EML file: ${err instanceof Error ? err.message : 'Unknown error'}`);
        }
    };

    // Generate HTML from parsed email
    const generateEmailHtml = (email: ParsedEmail): string => {
        return `
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                        padding: 20px;
                        margin: 0;
                        background-color: #ffffff;
                        color: #333;
                        line-height: 1.6;
                        overflow-x: hidden;
                        word-wrap: break-word;
                        max-width: 100%;
                    }
                    .email-header {
                        border-bottom: 2px solid #e0e0e0;
                        padding-bottom: 15px;
                        margin-bottom: 20px;
                    }
                    .email-field {
                        margin: 8px 0;
                    }
                    .email-label {
                        font-weight: 600;
                        color: #666;
                        display: inline-block;
                        min-width: 80px;
                    }
                    .email-value {
                        color: #333;
                    }
                    .email-subject {
                        font-size: 1.3em;
                        font-weight: 600;
                        margin: 15px 0;
                        color: #000;
                    }
                    .email-body {
                        margin-top: 20px;
                        padding: 15px;
                        background-color: #fafafa;
                        border-radius: 4px;
                        overflow-x: hidden;
                        word-wrap: break-word;
                        max-width: 100%;
                    }
                    .attachment-list {
                        margin-top: 20px;
                        padding: 15px;
                        background-color: #f5f5f5;
                        border-left: 3px solid #0078d4;
                    }
                    .attachment-item {
                        margin: 5px 0;
                        color: #0078d4;
                    }
                </style>
            </head>
            <body>
                <div class="email-header">
                    ${email.subject ? `<div class="email-subject">${escapeHtml(email.subject)}</div>` : ''}
                    ${email.from ? `<div class="email-field"><span class="email-label">From:</span> <span class="email-value">${email.from.name ? escapeHtml(email.from.name) : ''} ${email.from.address ? `&lt;${escapeHtml(email.from.address)}&gt;` : ''}</span></div>` : ''}
                    ${email.to && email.to.length > 0 ? `<div class="email-field"><span class="email-label">To:</span> <span class="email-value">${email.to.map((addr: any) => {
                        const name = addr.name ? escapeHtml(addr.name) : '';
                        const address = addr.address ? `&lt;${escapeHtml(addr.address)}&gt;` : '';
                        return `${name} ${address}`.trim();
                    }).join(', ')}</span></div>` : ''}
                    ${email.cc && email.cc.length > 0 ? `<div class="email-field"><span class="email-label">CC:</span> <span class="email-value">${email.cc.map((addr: any) => {
                        const name = addr.name ? escapeHtml(addr.name) : '';
                        const address = addr.address ? `&lt;${escapeHtml(addr.address)}&gt;` : '';
                        return `${name} ${address}`.trim();
                    }).join(', ')}</span></div>` : ''}
                    ${email.date ? `<div class="email-field"><span class="email-label">Date:</span> <span class="email-value">${new Date(email.date).toLocaleString()}</span></div>` : ''}
                </div>
                <div class="email-body">
                    ${email.html || (email.text ? `<pre style="white-space: pre-wrap; font-family: inherit;">${escapeHtml(email.text)}</pre>` : '<p><em>No content</em></p>')}
                </div>
                ${email.attachments && email.attachments.length > 0 ? `
                    <div class="attachment-list">
                        <strong>Attachments (${email.attachments.length}):</strong>
                        ${email.attachments.map((att: any) => {
                            const filename = att.filename || 'unnamed';
                            return `<div class="attachment-item">📎 ${escapeHtml(filename)} (${formatBytes(att.size || 0)})</div>`;
                        }).join('')}
                    </div>
                ` : ''}
            </body>
            </html>
        `;
    };

    useEffect(() => {
        const fetchAndParseEmail = async () => {
            setIsLoading(true);
            setError(null);

            try {
                const token = client ? await getToken(client) : undefined;
                
                // Detect file type
                const isMsgFile = src.toLowerCase().endsWith('.msg');
                const isEmlFile = src.toLowerCase().endsWith('.eml');
                
                console.log(`Fetching ${isMsgFile ? 'MSG' : isEmlFile ? 'EML' : 'email'} file from:`, src);
                
                const response = await fetch(src, {
                    method: "GET",
                    headers: await getHeaders(token)
                });
                
                if (!response.ok) {
                    throw new Error(`Failed to fetch email: ${response.statusText}`);
                }

                const emailContent = await response.arrayBuffer();
                console.log("Email content fetched, size:", emailContent.byteLength);
                
                let parsedEmail: ParsedEmail;

                // Parse based on file type
                if (isMsgFile) {
                    console.log("Parsing as MSG file...");
                    parsedEmail = await parseMsgFile(emailContent);
                } else {
                    console.log("Parsing as EML file...");
                    parsedEmail = await parseEmlFile(emailContent);
                }

                // Generate HTML
                const html = generateEmailHtml(parsedEmail);
                console.log("Generated HTML length:", html.length);
                
                setEmailHtml(html);
                setIsLoading(false);
            } catch (err) {
                console.error("Error loading email:", err);
                setError(err instanceof Error ? err : new Error("Unknown error"));
                setIsLoading(false);
            }
        };

        if (src) {
            fetchAndParseEmail();
        }
    }, [src, client]);

    return (
        <div>
            {isLoading ? (
                <div className={`${styles.loading} ${styles.emailViewer}`}>
                    <Spinner size={SpinnerSize.large} label="Loading email..." />
                </div>
            ) : error ? (
                <div className={`${styles.error} ${styles.emailViewer}`}>
                    <MessageBar messageBarType={MessageBarType.error} isMultiline={false}>
                        {error.message}
                        <Link href={src} download>
                            Download the file
                        </Link>
                    </MessageBar>
                </div>
            ) : emailHtml ? (
                <div className={styles.emailContainer} style={height ? { height } : undefined}>
                    <IconButton
                        className={styles.downloadButton}
                        style={{ color: "black" }}
                        iconProps={{ iconName: "Save" }}
                        title={t("tooltips.save")}
                        ariaLabel={t("tooltips.save")}
                        href={src}
                        download
                    />
                    <iframe 
                        title="Email Viewer"
                        className={styles.emailFrame}
                        srcDoc={emailHtml}
                        sandbox="allow-same-origin"
                    />
                </div>
            ) : (
                <div className={`${styles.error} ${styles.emailViewer}`}>
                    <MessageBar messageBarType={MessageBarType.warning} isMultiline={false}>
                        No email content to display
                    </MessageBar>
                </div>
            )}
        </div>
    );
};