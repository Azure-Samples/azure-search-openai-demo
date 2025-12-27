import {
    DefaultButton,
    DetailsList,
    DetailsListLayoutMode,
    Dialog,
    DialogFooter,
    DialogType,
    IColumn,
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
import styles from "./TaskadePanel.module.css";

interface TaskadeProject {
    id: string;
    title: string;
    description?: string;
}

interface TaskadeTask {
    id: string;
    title: string;
    description?: string;
    completed: boolean;
    priority?: string;
}

export function TaskadePanel() {
    const [projects, setProjects] = useState<TaskadeProject[]>([]);
    const [selectedProject, setSelectedProject] = useState<string | null>(null);
    const [tasks, setTasks] = useState<TaskadeTask[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);
    const [searchQuery, setSearchQuery] = useState("");
    const [searchResults, setSearchResults] = useState<TaskadeProject[]>([]);
    const [searching, setSearching] = useState(false);

    // Dialog states
    const [showProjectDialog, setShowProjectDialog] = useState(false);
    const [showTaskDialog, setShowTaskDialog] = useState(false);
    const [newProjectTitle, setNewProjectTitle] = useState("");
    const [newProjectDesc, setNewProjectDesc] = useState("");
    const [newTaskTitle, setNewTaskTitle] = useState("");
    const [newTaskDesc, setNewTaskDesc] = useState("");

    useEffect(() => {
        loadProjects();
    }, []);

    useEffect(() => {
        if (selectedProject) {
            loadTasks(selectedProject);
        }
    }, [selectedProject]);

    useEffect(() => {
        const trimmed = searchQuery.trim();
        if (!trimmed || trimmed.length < 2) {
            setSearchResults([]);
            return;
        }

        const handle = setTimeout(() => {
            searchProjects(trimmed);
        }, 400);

        return () => clearTimeout(handle);
    }, [searchQuery]);

    const loadProjects = async () => {
        setLoading(true);
        try {
            const response = await fetch("/api/agents/taskade/projects");
            const data = await response.json();

            if (data.success) {
                setProjects(data.projects || []);
            } else {
                setError(data.error || "Failed to load projects");
            }
        } catch (e) {
            setError("Failed to load projects: " + e);
        } finally {
            setLoading(false);
        }
    };

    const loadTasks = async (projectId: string) => {
        setLoading(true);
        try {
            const response = await fetch(`/api/agents/taskade/projects/${projectId}/tasks`);
            const data = await response.json();

            if (data.success) {
                setTasks(data.tasks || []);
            } else {
                setError(data.error || "Failed to load tasks");
            }
        } catch (e) {
            setError("Failed to load tasks: " + e);
        } finally {
            setLoading(false);
        }
    };

    const searchProjects = async (query: string) => {
        setSearching(true);
        try {
            const response = await fetch(`/api/agents/taskade/search?q=${encodeURIComponent(query)}&scope=projects`);
            const data = await response.json();

            if (data.success) {
                setSearchResults(data.projects || []);
            } else {
                setError(data.error || "Failed to search projects");
                setSearchResults([]);
            }
        } catch (e) {
            setError("Failed to search projects: " + e);
            setSearchResults([]);
        } finally {
            setSearching(false);
        }
    };

    const createProject = async () => {
        try {
            const response = await fetch("/api/agents/taskade/projects", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    title: newProjectTitle,
                    description: newProjectDesc
                })
            });

            const data = await response.json();

            if (data.success) {
                setSuccess("Project created successfully!");
                setShowProjectDialog(false);
                setNewProjectTitle("");
                setNewProjectDesc("");
                loadProjects();
            } else {
                setError(data.error || "Failed to create project");
            }
        } catch (e) {
            setError("Failed to create project: " + e);
        }
    };

    const createTask = async () => {
        if (!selectedProject) return;

        try {
            const response = await fetch(`/api/agents/taskade/projects/${selectedProject}/tasks`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    title: newTaskTitle,
                    description: newTaskDesc
                })
            });

            const data = await response.json();

            if (data.success) {
                setSuccess("Task created successfully!");
                setShowTaskDialog(false);
                setNewTaskTitle("");
                setNewTaskDesc("");
                loadTasks(selectedProject);
            } else {
                setError(data.error || "Failed to create task");
            }
        } catch (e) {
            setError("Failed to create task: " + e);
        }
    };

    const projectColumns: IColumn[] = [
        {
            key: "title",
            name: "Project",
            fieldName: "title",
            minWidth: 200,
            maxWidth: 400,
            isResizable: true
        },
        {
            key: "actions",
            name: "Actions",
            minWidth: 100,
            maxWidth: 150,
            onRender: (item: TaskadeProject) => <PrimaryButton text="View Tasks" onClick={() => setSelectedProject(item.id)} />
        }
    ];

    const taskColumns: IColumn[] = [
        {
            key: "title",
            name: "Task",
            fieldName: "title",
            minWidth: 200,
            maxWidth: 400,
            isResizable: true
        },
        {
            key: "status",
            name: "Status",
            minWidth: 80,
            maxWidth: 100,
            onRender: (item: TaskadeTask) => (
                <span className={item.completed ? styles.statusCompleted : styles.statusPending}>{item.completed ? "✅ Done" : "⏳ Pending"}</span>
            )
        },
        {
            key: "priority",
            name: "Priority",
            fieldName: "priority",
            minWidth: 80,
            maxWidth: 100
        }
    ];

    return (
        <Stack tokens={{ childrenGap: 20 }}>
            <Text variant="xLarge">Taskade Integration</Text>

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

            {/* Projects Section */}
            <Stack>
                <Stack tokens={{ childrenGap: 10 }}>
                    <TextField
                        label="Search Taskade"
                        placeholder="Type at least 2 characters to search across projects"
                        value={searchQuery}
                        onChange={(_, value) => setSearchQuery(value || "")}
                    />
                    {searchQuery.trim().length >= 2 && (
                        <Stack>
                            {searching ? (
                                <Spinner label="Searching Taskade..." />
                            ) : searchResults.length === 0 ? (
                                <MessageBar>No matches for your query.</MessageBar>
                            ) : (
                                <DetailsList
                                    items={searchResults}
                                    columns={projectColumns}
                                    setKey="search"
                                    layoutMode={DetailsListLayoutMode.justified}
                                    selectionMode={SelectionMode.none}
                                />
                            )}
                        </Stack>
                    )}
                </Stack>

                <Stack horizontal horizontalAlign="space-between" verticalAlign="center">
                    <Text variant="large">Projects ({projects.length})</Text>
                    <Stack horizontal tokens={{ childrenGap: 10 }}>
                        <PrimaryButton text="New Project" onClick={() => setShowProjectDialog(true)} />
                        <DefaultButton text="Refresh" onClick={loadProjects} disabled={loading} />
                    </Stack>
                </Stack>

                {loading ? (
                    <Spinner label="Loading projects..." />
                ) : projects.length === 0 ? (
                    <MessageBar>No projects found. Create your first project!</MessageBar>
                ) : (
                    <DetailsList
                        items={projects}
                        columns={projectColumns}
                        setKey="set"
                        layoutMode={DetailsListLayoutMode.justified}
                        selectionMode={SelectionMode.none}
                    />
                )}
            </Stack>

            {/* Tasks Section */}
            {selectedProject && (
                <Stack className={styles.tasksSection}>
                    <Stack horizontal horizontalAlign="space-between" verticalAlign="center">
                        <Text variant="large">Tasks ({tasks.length})</Text>
                        <Stack horizontal tokens={{ childrenGap: 10 }}>
                            <PrimaryButton text="New Task" onClick={() => setShowTaskDialog(true)} />
                            <DefaultButton text="Back to Projects" onClick={() => setSelectedProject(null)} />
                        </Stack>
                    </Stack>

                    {tasks.length === 0 ? (
                        <MessageBar>No tasks in this project.</MessageBar>
                    ) : (
                        <DetailsList
                            items={tasks}
                            columns={taskColumns}
                            setKey="set"
                            layoutMode={DetailsListLayoutMode.justified}
                            selectionMode={SelectionMode.none}
                        />
                    )}
                </Stack>
            )}

            {/* Create Project Dialog */}
            <Dialog
                hidden={!showProjectDialog}
                onDismiss={() => setShowProjectDialog(false)}
                dialogContentProps={{
                    type: DialogType.normal,
                    title: "Create New Project"
                }}
            >
                <Stack tokens={{ childrenGap: 15 }}>
                    <TextField label="Project Title" value={newProjectTitle} onChange={(_, value) => setNewProjectTitle(value || "")} required />
                    <TextField label="Description" value={newProjectDesc} onChange={(_, value) => setNewProjectDesc(value || "")} multiline rows={3} />
                </Stack>
                <DialogFooter>
                    <PrimaryButton onClick={createProject} text="Create" disabled={!newProjectTitle} />
                    <DefaultButton onClick={() => setShowProjectDialog(false)} text="Cancel" />
                </DialogFooter>
            </Dialog>

            {/* Create Task Dialog */}
            <Dialog
                hidden={!showTaskDialog}
                onDismiss={() => setShowTaskDialog(false)}
                dialogContentProps={{
                    type: DialogType.normal,
                    title: "Create New Task"
                }}
            >
                <Stack tokens={{ childrenGap: 15 }}>
                    <TextField label="Task Title" value={newTaskTitle} onChange={(_, value) => setNewTaskTitle(value || "")} required />
                    <TextField label="Description" value={newTaskDesc} onChange={(_, value) => setNewTaskDesc(value || "")} multiline rows={3} />
                </Stack>
                <DialogFooter>
                    <PrimaryButton onClick={createTask} text="Create" disabled={!newTaskTitle} />
                    <DefaultButton onClick={() => setShowTaskDialog(false)} text="Cancel" />
                </DialogFooter>
            </Dialog>
        </Stack>
    );
}
