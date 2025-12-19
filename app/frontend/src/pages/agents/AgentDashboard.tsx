import { DefaultButton, MessageBar, MessageBarType, Stack, Text } from "@fluentui/react";
import { useEffect, useState } from "react";
import styles from "./AgentDashboard.module.css";

import { BrowserAgentPanel } from "./BrowserAgentPanel";
import { MCPPanel } from "./MCPPanel";
import { TaskadePanel } from "./TaskadePanel";

export function AgentDashboard() {
    const [activeTab, setActiveTab] = useState<"browser" | "taskade" | "mcp">("browser");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [healthStatus, setHealthStatus] = useState<any>(null);

    useEffect(() => {
        checkHealth();
    }, []);

    const checkHealth = async () => {
        try {
            const response = await fetch("/api/agents/health");
            const data = await response.json();
            setHealthStatus(data);
        } catch (e) {
            console.error("Health check failed:", e);
        }
    };

    return (
        <div className={styles.container}>
            <Stack tokens={{ childrenGap: 20 }}>
                {/* Header */}
                <Stack horizontal horizontalAlign="space-between" verticalAlign="center">
                    <Stack>
                        <Text variant="xxLarge" className={styles.title}>
                            🤖 Agent Management Dashboard
                        </Text>
                        <Text variant="medium" className={styles.subtitle}>
                            Control browser agents, Taskade integration, and MCP tasks
                        </Text>
                    </Stack>
                    {healthStatus && (
                        <Stack horizontal tokens={{ childrenGap: 10 }}>
                            <div className={styles.statusIndicator} />
                            <Text variant="small">System Online</Text>
                        </Stack>
                    )}
                </Stack>

                {error && (
                    <MessageBar messageBarType={MessageBarType.error} onDismiss={() => setError(null)}>
                        {error}
                    </MessageBar>
                )}

                {/* Tab Navigation */}
                <Stack horizontal tokens={{ childrenGap: 10 }} className={styles.tabBar}>
                    <DefaultButton
                        text="🌐 Browser Agents"
                        onClick={() => setActiveTab("browser")}
                        className={activeTab === "browser" ? styles.activeTab : styles.tab}
                    />
                    <DefaultButton
                        text="📋 Taskade"
                        onClick={() => setActiveTab("taskade")}
                        className={activeTab === "taskade" ? styles.activeTab : styles.tab}
                    />
                    <DefaultButton text="🔄 MCP Tasks" onClick={() => setActiveTab("mcp")} className={activeTab === "mcp" ? styles.activeTab : styles.tab} />
                </Stack>

                {/* Content Panels */}
                <div className={styles.content}>
                    {activeTab === "browser" && <BrowserAgentPanel />}
                    {activeTab === "taskade" && <TaskadePanel />}
                    {activeTab === "mcp" && <MCPPanel />}
                </div>
            </Stack>
        </div>
    );
}
