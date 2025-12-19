import {
    DefaultButton,
    DetailsList,
    DetailsListLayoutMode,
    Dialog,
    DialogFooter,
    DialogType,
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
    TextField
} from "@fluentui/react";
import { useEffect, useState } from "react";
import styles from "./MCPPanel.module.css";

interface MCPTask {
    id: string;
    title: string;
    description: string;
    task_type: string;
    platform: string;
    status: string;
    priority: string;
    created_at: string;
}

export function MCPPanel() {
    const [tasks, setTasks] = useState<MCPTask[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);

    // Dialog state
    const [showDialog, setShowDialog] = useState(false);
    const [newTaskTitle, setNewTaskTitle] = useState("");
    const [newTaskDesc, setNewTaskDesc] = useState("");
    const [newTaskType, setNewTaskType] = useState("registration");
    const [newTaskPlatform, setNewTaskPlatform] = useState("upwork");
    const [newTaskPriority, setNewTaskPriority] = useState("medium");

    useEffect(() => {
        loadTasks();
    }, []);

    const loadTasks = async () => {
        setLoading(true);
        try {
            const response = await fetch("/api/agents/mcp/tasks");
            const data = await response.json();

            if (data.success) {
                setTasks(data.tasks || []);
            } else {
                setError(data.error || "Failed to load tasks");
            }
        } catch (e) {
            setError("Failed to load MCP tasks: " + e);
        } finally {
            setLoading(false);
        }
    };

    const createTask = async () => {
        try {
            const response = await fetch("/api/agents/mcp/tasks", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    title: newTaskTitle,
                    description: newTaskDesc,
                    task_type: newTaskType,
                    platform: newTaskPlatform,
                    priority: newTaskPriority
                })
            });

            const data = await response.json();

            if (data.success) {
                setSuccess("MCP task created successfully!");
                setShowDialog(false);
                resetForm();
                loadTasks();
            } else {
                setError(data.error || "Failed to create task");
            }
        } catch (e) {
            setError("Failed to create task: " + e);
        }
    };

    const resetForm = () => {
        setNewTaskTitle("");
        setNewTaskDesc("");
        setNewTaskType("registration");
        setNewTaskPlatform("upwork");
        setNewTaskPriority("medium");
    };

    const taskTypeOptions: IDropdownOption[] = [
        { key: "registration", text: "Registration" },
        { key: "api_setup", text: "API Setup" },
        { key: "webhook_setup", text: "Webhook Setup" },
        { key: "generic", text: "Generic" }
    ];

    const platformOptions: IDropdownOption[] = [
        { key: "upwork", text: "Upwork" },
        { key: "fiverr", text: "Fiverr" },
        { key: "freelancer", text: "Freelancer" },
        { key: "toptal", text: "Toptal" },
        { key: "other", text: "Other" }
    ];

    const priorityOptions: IDropdownOption[] = [
        { key: "low", text: "Low" },
        { key: "medium", text: "Medium" },
        { key: "high", text: "High" },
        { key: "urgent", text: "Urgent" }
    ];

    const getStatusColor = (status: string) => {
        switch (status) {
            case "completed":
                return styles.statusCompleted;
            case "running":
                return styles.statusRunning;
            case "failed":
                return styles.statusFailed;
            case "pending":
                return styles.statusPending;
            default:
                return "";
        }
    };

    const columns: IColumn[] = [
        {
            key: "title",
            name: "Task",
            fieldName: "title",
            minWidth: 200,
            maxWidth: 300,
            isResizable: true
        },
        {
            key: "task_type",
            name: "Type",
            fieldName: "task_type",
            minWidth: 100,
            maxWidth: 120,
            isResizable: true
        },
        {
            key: "platform",
            name: "Platform",
            fieldName: "platform",
            minWidth: 80,
            maxWidth: 100,
            isResizable: true
        },
        {
            key: "status",
            name: "Status",
            fieldName: "status",
            minWidth: 100,
            maxWidth: 120,
            isResizable: true,
            onRender: (item: MCPTask) => <span className={getStatusColor(item.status)}>{item.status.toUpperCase()}</span>
        },
        {
            key: "priority",
            name: "Priority",
            fieldName: "priority",
            minWidth: 80,
            maxWidth: 100,
            isResizable: true
        }
    ];

    return (
        <Stack tokens={{ childrenGap: 20 }}>
            <Text variant="xLarge">MCP Task Queue</Text>

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

            {/* Tasks List */}
            <Stack>
                <Stack horizontal horizontalAlign="space-between" verticalAlign="center">
                    <Text variant="large">Tasks ({tasks.length})</Text>
                    <Stack horizontal tokens={{ childrenGap: 10 }}>
                        <PrimaryButton text="New Task" onClick={() => setShowDialog(true)} />
                        <DefaultButton text="Refresh" onClick={loadTasks} disabled={loading} />
                    </Stack>
                </Stack>

                {loading ? (
                    <Spinner label="Loading tasks..." />
                ) : tasks.length === 0 ? (
                    <MessageBar>No MCP tasks in queue. Create one to get started.</MessageBar>
                ) : (
                    <DetailsList items={tasks} columns={columns} setKey="set" layoutMode={DetailsListLayoutMode.justified} selectionMode={SelectionMode.none} />
                )}
            </Stack>

            {/* Create Task Dialog */}
            <Dialog
                hidden={!showDialog}
                onDismiss={() => setShowDialog(false)}
                dialogContentProps={{
                    type: DialogType.normal,
                    title: "Create MCP Task"
                }}
            >
                <Stack tokens={{ childrenGap: 15 }}>
                    <TextField label="Task Title" value={newTaskTitle} onChange={(_, value) => setNewTaskTitle(value || "")} required />
                    <TextField label="Description" value={newTaskDesc} onChange={(_, value) => setNewTaskDesc(value || "")} multiline rows={3} />
                    <Dropdown
                        label="Task Type"
                        selectedKey={newTaskType}
                        onChange={(_, option) => setNewTaskType(option!.key as string)}
                        options={taskTypeOptions}
                    />
                    <Dropdown
                        label="Platform"
                        selectedKey={newTaskPlatform}
                        onChange={(_, option) => setNewTaskPlatform(option!.key as string)}
                        options={platformOptions}
                    />
                    <Dropdown
                        label="Priority"
                        selectedKey={newTaskPriority}
                        onChange={(_, option) => setNewTaskPriority(option!.key as string)}
                        options={priorityOptions}
                    />
                </Stack>
                <DialogFooter>
                    <PrimaryButton onClick={createTask} text="Create" disabled={!newTaskTitle} />
                    <DefaultButton onClick={() => setShowDialog(false)} text="Cancel" />
                </DialogFooter>
            </Dialog>
        </Stack>
    );
}
