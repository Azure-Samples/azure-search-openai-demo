import {
    DefaultButton,
    DetailsList,
    DetailsListLayoutMode,
    Dropdown,
    IColumn,
    IDropdownOption,
    MessageBar,
    MessageBarType,
    PrimaryButton,
    SelectionMode,
    Spinner,
    Stack,
    Text,
    Toggle
} from "@fluentui/react";
import { useEffect, useState } from "react";
import styles from "./BrowserAgentPanel.module.css";

interface BrowserAgent {
    id: string;
    status: string;
    config: {
        headless: boolean;
        viewport: {
            width: number;
            height: number;
        };
    };
}

export function BrowserAgentPanel() {
    const [agents, setAgents] = useState<BrowserAgent[]>([]);
    const [loading, setLoading] = useState(false);
    const [creating, setCreating] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);

    // New agent config
    const [headless, setHeadless] = useState(false);
    const [browserChannel, setBrowserChannel] = useState("msedge");

    useEffect(() => {
        loadAgents();
    }, []);

    const loadAgents = async () => {
        setLoading(true);
        try {
            const response = await fetch("/api/agents/browser");
            const data = await response.json();
            setAgents(data.agents || []);
        } catch (e) {
            setError("Failed to load agents: " + e);
        } finally {
            setLoading(false);
        }
    };

    const createAgent = async () => {
        setCreating(true);
        setError(null);
        setSuccess(null);

        try {
            const response = await fetch("/api/agents/browser", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    config: {
                        headless,
                        channel: browserChannel
                    }
                })
            });

            const data = await response.json();

            if (data.success) {
                setSuccess(`Agent ${data.agent_id} started successfully!`);
                loadAgents();
            } else {
                setError(data.error || "Failed to create agent");
            }
        } catch (e) {
            setError("Failed to create agent: " + e);
        } finally {
            setCreating(false);
        }
    };

    const stopAgent = async (agentId: string) => {
        try {
            const response = await fetch(`/api/agents/browser/${agentId}`, {
                method: "DELETE"
            });

            const data = await response.json();

            if (data.success) {
                setSuccess(`Agent ${agentId} stopped`);
                loadAgents();
            } else {
                setError(data.error || "Failed to stop agent");
            }
        } catch (e) {
            setError("Failed to stop agent: " + e);
        }
    };

    const browserOptions: IDropdownOption[] = [
        { key: "msedge", text: "Microsoft Edge" },
        { key: "chrome", text: "Chrome" },
        { key: "chromium", text: "Chromium" }
    ];

    const columns: IColumn[] = [
        {
            key: "id",
            name: "Agent ID",
            fieldName: "id",
            minWidth: 150,
            maxWidth: 250,
            isResizable: true
        },
        {
            key: "status",
            name: "Status",
            fieldName: "status",
            minWidth: 80,
            maxWidth: 100,
            isResizable: true,
            onRender: (item: BrowserAgent) => (
                <span className={item.status === "active" ? styles.statusActive : styles.statusStopped}>
                    {item.status === "active" ? "🟢 Active" : "🔴 Stopped"}
                </span>
            )
        },
        {
            key: "headless",
            name: "Mode",
            minWidth: 80,
            maxWidth: 100,
            isResizable: true,
            onRender: (item: BrowserAgent) => <span>{item.config.headless ? "Headless" : "UI"}</span>
        },
        {
            key: "actions",
            name: "Actions",
            minWidth: 100,
            maxWidth: 150,
            onRender: (item: BrowserAgent) => <DefaultButton text="Stop" onClick={() => stopAgent(item.id)} />
        }
    ];

    return (
        <Stack tokens={{ childrenGap: 20 }}>
            <Text variant="xLarge">Browser Agents (Edge)</Text>

            {error && (
                <MessageBar messageBarType={MessageBarType.error} onDismiss={() => setError(null)}>
                    {error}
                </MessageBar>
            )}

            {success && (
                <MessageBar messageBarType={MessageBarType.success} onDismiss={() => setSuccess(null)}>
                    {success}
                </MessageBar>
            )}

            {/* Create Agent Form */}
            <Stack className={styles.createForm} tokens={{ childrenGap: 15 }}>
                <Text variant="large">Create New Agent</Text>

                <Dropdown
                    label="Browser"
                    selectedKey={browserChannel}
                    onChange={(_, option) => setBrowserChannel(option!.key as string)}
                    options={browserOptions}
                    disabled={creating}
                />

                <Toggle
                    label="Headless Mode"
                    checked={headless}
                    onChange={(_, checked) => setHeadless(!!checked)}
                    disabled={creating}
                    onText="Headless (no UI)"
                    offText="UI Mode (visible)"
                />

                <PrimaryButton text="Start Agent" onClick={createAgent} disabled={creating}>
                    {creating && <Spinner />}
                </PrimaryButton>
            </Stack>

            {/* Agents List */}
            <Stack>
                <Stack horizontal horizontalAlign="space-between" verticalAlign="center">
                    <Text variant="large">Active Agents ({agents.length})</Text>
                    <DefaultButton text="Refresh" onClick={loadAgents} disabled={loading} />
                </Stack>

                {loading ? (
                    <Spinner label="Loading agents..." />
                ) : agents.length === 0 ? (
                    <MessageBar>No active agents. Create one to get started.</MessageBar>
                ) : (
                    <DetailsList
                        items={agents}
                        columns={columns}
                        setKey="set"
                        layoutMode={DetailsListLayoutMode.justified}
                        selectionMode={SelectionMode.none}
                        className={styles.agentsList}
                    />
                )}
            </Stack>
        </Stack>
    );
}
