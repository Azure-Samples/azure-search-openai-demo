import React, { useState, useEffect, FormEvent, useCallback } from "react";
import { useDropzone } from "react-dropzone";

import {
    TableBody,
    TableCell,
    TableRow,
    Table,
    TableHeader,
    TableHeaderCell,
    Accordion,
    AccordionItem,
    AccordionHeader,
    AccordionPanel,
    Button,
    Dialog,
    DialogTrigger,
    DialogSurface,
    DialogTitle,
    DialogBody,
    DialogActions,
    DialogContent,
    Input,
    Label,
    Dropdown,
    Option,
    TableCellLayout,
    Spinner,
    TableColumnSizingOptions,
    useTableFeatures,
    TableColumnDefinition,
    createTableColumn,
    useTableColumnSizing_unstable
} from "@fluentui/react-components";

import { Premium20Regular, Edit20Regular, Eye20Regular, EyeOff20Regular, Dismiss20Filled, DocumentArrowUpRegular } from "@fluentui/react-icons";
import styles from "./Manage.module.css";
import { auth } from "../..";
import axios from "axios";
import { onAuthStateChanged } from "firebase/auth";
import { v4 as uuidv4 } from "uuid";

export default function Manage(): JSX.Element {
    const [currentUser, setCurrentUser] = useState<User | null>(null);
    const [projects, setProjects] = useState<Project[]>([]);
    const [loading, setLoading] = useState(true);
    const [newUserInputs, setNewUserInputs] = useState<User>({
        uuid: "",
        emailAddress: "",
        firstName: "",
        lastName: "",
        initialPasswordChanged: false,
        projectName: "",
        projectID: "",
        projectRole: "Member"
    });
    const [newProjectInputs, setNewProjectInputs] = useState<NewProject>({
        projectID: "",
        projectName: "",
        dateCreated: ""
    });
    const [openCreateUser, setOpenCreateUser] = useState(false);
    const [showPassword, setShowPassword] = useState(false);
    const [openCreateProject, setOpenCreateProject] = useState(false);
    const [openSettingsDialog, setOpenSettingsDialog] = useState(false);
    const [newUserRole, setNewUserRole] = useState("Member");

    const [selectedUser, setSelectedUser] = useState<User | null>(null);
    const [selectedProject, setSelectedProject] = useState<Project | null>(null);

    const baseURL = import.meta.env.VITE_FIREBASE_BASE_URL;
    const baseURL2 = "http://127.0.0.1:5001/projectpalai-83a5f/us-central1/";

    // const columnsDef = [
    //     { columnKey: "firstName", name: "First Name" },
    //     { columnKey: "lastName", name: "Last Name" },
    //     { columnKey: "emailAddress", name: "User Email" },
    //     { columnKey: "projectRole", name: "Project Role" },
    //     { columnKey: "initialPasswordChanged", name: "Initial Password Changed" },
    //     { columnKey: "edit", name: "Edit" }
    // ];
    type firstNameCell = {
        label: string;
        icon: string | JSX.Element;
    };
    type editCell = {
        label: string;
        icon: string | JSX.Element;
    };

    type Item = {
        projectId: string;
        firstName: firstNameCell;
        lastName: string;
        emailAddress: string;
        projectRole: string;
        initialPasswordChanged: string;
        edit: editCell;
    };

    const columnsDef: TableColumnDefinition<Item>[] = [
        createTableColumn<Item>({ columnId: "firstName", renderHeaderCell: () => <h3>First Name</h3> }),
        createTableColumn<Item>({ columnId: "lastName", renderHeaderCell: () => <h3>Last Name</h3> }),
        createTableColumn<Item>({ columnId: "emailAddress", renderHeaderCell: () => <h3>User Email</h3> }),
        createTableColumn<Item>({ columnId: "projectRole", renderHeaderCell: () => <h3>Project Role</h3> }),
        createTableColumn<Item>({ columnId: "initialPasswordChanged", renderHeaderCell: () => <h3>Initial Password Changed</h3> }),
        createTableColumn<Item>({ columnId: "edit", renderHeaderCell: () => <h3>Edit</h3> })
    ];

    const [columnSizingOptions] = React.useState<TableColumnSizingOptions>({
        projectId: {
            idealWidth: 0
        },
        firstName: {
            idealWidth: 150
        },
        lastName: {
            idealWidth: 150
        },
        emailAddress: {
            minWidth: 200
        },
        projectRole: {
            idealWidth: 100
        },
        initialPasswordChanged: {
            idealWidth: 200
        },
        edit: {
            idealWidth: 100
        }
    });

    const items: Item[] = projects.flatMap(project =>
        project.users
            ? project.users.map(user => ({
                  projectId: project.projectID,
                  firstName: { label: user.firstName, icon: user.projectRole === "Owner" || user.projectRole === "Admin" ? <Premium20Regular /> : "" },
                  lastName: user.lastName,
                  emailAddress: user.emailAddress,
                  projectRole: user.projectRole || "Member",
                  initialPasswordChanged: user.initialPasswordChanged ? "Yes" : "No",
                  edit: {
                      label: "",
                      icon:
                          currentUser?.projectRole === "Owner" || currentUser?.projectRole === "Admin" ? (
                              <Edit20Regular style={{ cursor: "pointer" }} onClick={() => handleEditClick(user, project)} />
                          ) : (
                              <Dismiss20Filled style={{ cursor: "pointer" }} />
                          )
                  }
              }))
            : []
    );
    const [columns] = React.useState<TableColumnDefinition<Item>[]>(columnsDef);

    const { getRows, columnSizing_unstable, tableRef } = useTableFeatures({ columns, items }, [useTableColumnSizing_unstable({ columnSizingOptions })]);

    const rows = getRows();

    const handleOpenCreateUser = (project: Project) => {
        setOpenCreateUser(true);
        setNewUserInputs({
            ...newUserInputs,
            projectName: project.projectName,
            projectID: project.projectID
        });
    };
    const handleUserInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        const { name, value } = event.target;
        setNewUserInputs({ ...newUserInputs, [name]: value });
    };

    const handleProjectInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        const { name, value } = event.target;
        setNewProjectInputs({ ...newProjectInputs, [name]: value });
    };

    const handleEditClick = (user: User, project: Project) => {
        setSelectedUser(user);
        setSelectedProject(project);
        setOpenSettingsDialog(true);
        // console.log(selectedUser, selectedProject);
    };

    const handleCreateUserDB = (user: any) => {
        return axios.post(baseURL + "createNewAccount", user);
    };

    const handleAddUserToProject = (projectID: string, user: NewUser) => {
        return axios.post(baseURL + "addNewUserToProject", { projectID, user });
    };

    const handleCreateUser = (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        setLoading(true);
        const uuid = uuidv4();
        const emailAddress = newUserInputs?.emailAddress as string;
        const firstName = newUserInputs?.firstName as string;
        const lastName = newUserInputs?.lastName as string;
        const projectRole = newUserInputs?.projectRole as string;
        const projectID = newUserInputs?.projectID as string;
        const password = newUserInputs?.password as string;

        const newUser: User = {
            uuid: uuid,
            emailAddress: emailAddress,
            firstName: firstName,
            lastName: lastName,
            initialPasswordChanged: false,
            password: password
        };

        const newUserProject: NewUser = {
            uuid: uuid,
            emailAddress: emailAddress,
            projectRole: projectRole,
            projectID: projectID
        };

        handleCreateUserDB(newUser).then(response => {
            handleAddUserToProject(projectID, newUserProject).then(response => {
                if (response.data === "User already exists in project") {
                    setLoading(false);
                    setOpenCreateUser(false);
                    return;
                } else {
                    newUser.uuid = response.data.uuid;
                    newUser.projectRole = response.data.projectRole;
                    projects.forEach(project => {
                        if (project.projectID === projectID && project.users) {
                            project.users.push(newUser);
                        } else if (project.projectID === projectID) {
                            project.users = [newUser];
                        }
                    });

                    setNewUserInputs({
                        uuid: "",
                        emailAddress: "",
                        firstName: "",
                        lastName: "",
                        initialPasswordChanged: false,
                        projectName: "",
                        projectID: "",
                        projectRole: "Member"
                    });
                    setLoading(false);
                    setOpenCreateUser(false);
                }
            });
        });
        // axios.post(baseURL + "createNewAccount", newUser).then(response => {
        //     axios.post(baseURL + "addNewUserToProject", { projectID, newUserProject }).then(response => {});
        // })
    };

    const handleCreateProject = (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        setLoading(true);
        const projectID = uuidv4();
        const projectName = newProjectInputs?.projectName as string;
        const newProject: NewProject = {
            projectID: projectID,
            projectName: projectName,
            dateCreated: new Date().toISOString()
        };
        axios.post(baseURL + "createNewProject", newProject).then(response => {
            console.log("New project created");
            setProjects([...projects, response.data]);
            setNewProjectInputs({
                projectID: "",
                projectName: "",
                dateCreated: ""
            });
            setLoading(false);
            setOpenCreateProject(false);
        });
    };

    const handleRemoveUser = (projectID: string, user: User) => {
        setLoading(true);
        axios.post(baseURL + "removeUserFromProject", { projectID: projectID, uuid: user.uuid, projectRole: user.projectRole }).then(response => {
            console.log("User removed from project");
            projects.forEach(project => {
                if (project.users.some(user => user.uuid === user.uuid) && projectID === project.projectID) {
                    project.users = project.users.filter(projectUser => projectUser.uuid !== user.uuid);
                }
            });
            setLoading(false);
            setOpenSettingsDialog(false);
        });
    };

    const handleChangeUserRole = (projectID: string, user: User, newRole: string) => {
        setLoading(true);
        if (user.projectRole === newRole) {
            return;
        }
        axios.post(baseURL + "changeUserRole", { projectID: projectID, user: user, newRole: newRole }).then(response => {
            console.log("User role changed");
            projects.forEach(project => {
                if (project.users && projectID === project.projectID) {
                    project.users.forEach(projectUser => {
                        if (projectUser.uuid === user.uuid) {
                            projectUser.projectRole = newRole;
                        }
                    });
                }
            });
            setNewUserRole("Member");
            setLoading(false);
            setOpenSettingsDialog(false);
        });
    };

    function Dropzone({ projectID }: { projectID: string }) {
        const [filePath, setFilePath] = useState("");
        const onDrop = useCallback((acceptedFiles: any) => {
            //@cade-ryan - handle file uploads here
            acceptedFiles.forEach((file: any) => {
                setFilePath(file.path);
                const reader = new FileReader();

                reader.onabort = () => console.log("file reading was aborted");
                reader.onerror = () => console.log("file reading has failed");
                reader.onload = () => {
                    // Do whatever you want with the file contents
                    const binaryStr = reader.result;
                };
                reader.readAsArrayBuffer(file);
            });
        }, []);
        const { getRootProps, getInputProps } = useDropzone({ onDrop });
        return (
            <>
                <div {...getRootProps()} className={styles.dropzone} key={projectID}>
                    <input {...getInputProps()} />
                    {!filePath && (
                        <>
                            <DocumentArrowUpRegular fontSize={40} style={{ color: "#409ece" }} />
                            <p style={{ margin: "0", textAlign: "center" }}>Drag and drop your project files here</p>
                        </>
                    )}
                    {filePath && (
                        <>
                            <DocumentArrowUpRegular fontSize={40} style={{ color: "#409ece" }} />
                            <p>{filePath}</p>
                        </>
                    )}
                </div>
            </>
        );
    }

    useEffect(() => {
        const unsubscribe = onAuthStateChanged(auth, user => {
            if (user) {
                axios.get(baseURL + "getAccountDetails", { params: { clientID: user.uid } }).then(response => {
                    const data = response.data;
                    if (data.found) {
                        setCurrentUser(data.user);
                        axios.get(baseURL + "getProjects", { params: { clientID: user.uid } }).then(response => {
                            setProjects(response.data);
                            setLoading(false);
                        });
                    }
                });
            }
        });
        return () => unsubscribe();
    }, []);
    return (
        <div className={styles.container}>
            <h1>Manage {currentUser && currentUser.projectRole && `(Viewing as ${currentUser.projectRole})`}</h1>
            {loading && <Spinner label="Loading..." labelPosition="below" size="large" />}
            <div className={styles.projects}>
                <Accordion collapsible multiple>
                    {projects.map((project, index) => (
                        <AccordionItem key={index} value={index}>
                            <AccordionHeader>
                                {" "}
                                <h3>{project.projectName}</h3>
                            </AccordionHeader>
                            <AccordionPanel>
                                <div className={styles.accordionRow}>
                                    <div style={{ maxWidth: "950px" }}>
                                        <Table sortable aria-label="Project table" ref={tableRef} {...columnSizing_unstable.getTableProps()}>
                                            <TableHeader>
                                                <TableRow>
                                                    {columns.map(column => (
                                                        <TableHeaderCell
                                                            key={column.columnId}
                                                            {...columnSizing_unstable.getTableHeaderCellProps(column.columnId)}
                                                        >
                                                            {column.renderHeaderCell()}
                                                        </TableHeaderCell>
                                                    ))}
                                                </TableRow>
                                            </TableHeader>

                                            <TableBody>
                                                {rows.map(
                                                    ({ item }) =>
                                                        item.projectId === project.projectID && (
                                                            <TableRow key={item.firstName.label}>
                                                                <TableCell {...columnSizing_unstable.getTableCellProps("firstName")}>
                                                                    <TableCellLayout media={item.firstName.icon}>{item.firstName.label}</TableCellLayout>
                                                                </TableCell>
                                                                <TableCell {...columnSizing_unstable.getTableCellProps("lastName")}>{item.lastName}</TableCell>
                                                                <TableCell {...columnSizing_unstable.getTableCellProps("emailAddress")}>
                                                                    {item.emailAddress}
                                                                </TableCell>
                                                                <TableCell {...columnSizing_unstable.getTableCellProps("projectRole")}>
                                                                    {item.projectRole}
                                                                </TableCell>
                                                                <TableCell {...columnSizing_unstable.getTableCellProps("initialPasswordChanged")}>
                                                                    {item.initialPasswordChanged}
                                                                </TableCell>
                                                                <TableCell {...columnSizing_unstable.getTableCellProps("edit")}>{item.edit.icon}</TableCell>
                                                            </TableRow>
                                                        )
                                                )}
                                            </TableBody>
                                        </Table>
                                    </div>
                                    <Dropzone projectID={project.projectID} />
                                </div>
                                {currentUser &&
                                    (currentUser.projectRole === "Admin" ||
                                        currentUser.projectRole === "Owner" ||
                                        (project.users && project.users.some(user => user.uuid === currentUser.uuid && user.projectRole === "Owner"))) && (
                                        <Button
                                            appearance="primary"
                                            onClick={() => handleOpenCreateUser(project)}
                                            style={{ marginTop: "10px", backgroundColor: "green" }}
                                        >
                                            Create new user
                                        </Button>
                                    )}
                            </AccordionPanel>
                        </AccordionItem>
                    ))}
                </Accordion>

                {currentUser && currentUser.projectRole === "Admin" && (
                    <Button style={{ width: "150px" }} appearance="primary" onClick={() => setOpenCreateProject(true)}>
                        Create new Project
                    </Button>
                )}

                <Dialog open={openCreateProject} onOpenChange={(_, data) => setOpenCreateProject(data.open)}>
                    <DialogSurface style={{ maxWidth: "400px" }}>
                        <DialogBody
                            style={{
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                flexDirection: "column"
                            }}
                        >
                            <DialogTitle>Create new Project</DialogTitle>
                            <form onSubmit={handleCreateProject} style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
                                <DialogContent>
                                    <div className={`${styles.inputColumn} ${styles.edit}`}>
                                        <div className={styles.inputGroup}>
                                            <Label>Project Name</Label>
                                            <Input
                                                name="projectName"
                                                placeholder="Project Name"
                                                aria-label="Project Name"
                                                onChange={handleProjectInputChange}
                                                required
                                            />
                                            {loading && <Spinner label="Loading..." labelPosition="below" size="large" />}
                                        </div>
                                    </div>
                                </DialogContent>
                                <DialogActions style={{ justifyContent: "space-between" }}>
                                    <DialogTrigger disableButtonEnhancement>
                                        <Button appearance="secondary">Close</Button>
                                    </DialogTrigger>
                                    <Button appearance="primary" type="submit" disabled={loading}>
                                        Create Project
                                    </Button>
                                </DialogActions>
                            </form>
                        </DialogBody>
                    </DialogSurface>
                </Dialog>

                <Dialog open={openCreateUser} onOpenChange={(_, data) => setOpenCreateUser(data.open)}>
                    <DialogSurface style={{ maxWidth: "400px" }}>
                        <DialogBody
                            style={{
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                flexDirection: "column"
                            }}
                        >
                            <DialogTitle>Create new user</DialogTitle>
                            <form onSubmit={handleCreateUser} style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
                                <DialogContent>
                                    <div className={styles.inputColumn}>
                                        <div className={styles.inputGroup}>
                                            <Label>First Name</Label>
                                            <Input
                                                name="firstName"
                                                placeholder="First Name"
                                                aria-label="First Name"
                                                onChange={handleUserInputChange}
                                                required
                                            />
                                        </div>
                                        <div className={styles.inputGroup}>
                                            <Label>Last Name</Label>
                                            <Input name="lastName" placeholder="Last Name" aria-label="Last Name" onChange={handleUserInputChange} required />
                                        </div>
                                        <div className={styles.inputGroup}>
                                            <Label>Email Address</Label>
                                            <Input
                                                name="emailAddress"
                                                placeholder="Email Address"
                                                aria-label="Email Address"
                                                onChange={handleUserInputChange}
                                                required
                                                type="email"
                                            />
                                        </div>
                                        <div className={styles.inputGroup}>
                                            <Label>Password</Label>
                                            <Input
                                                id="passwordInput"
                                                name="password"
                                                placeholder="Password"
                                                aria-label="Password"
                                                onChange={handleUserInputChange}
                                                required
                                                type={showPassword ? "text" : "password"}
                                                contentAfter={
                                                    showPassword ? (
                                                        <EyeOff20Regular style={{ cursor: "pointer" }} onClick={() => setShowPassword(false)} />
                                                    ) : (
                                                        <Eye20Regular
                                                            style={{ cursor: "pointer" }}
                                                            onClick={() => {
                                                                setShowPassword(true);
                                                            }}
                                                        />
                                                    )
                                                }
                                            />
                                        </div>
                                        <div className={styles.inputGroup}>
                                            <Label>Project Role</Label>
                                            <Dropdown
                                                name="projectRole"
                                                defaultValue="Member"
                                                defaultSelectedOptions={["Member"]}
                                                onOptionSelect={(_, selected) => setNewUserInputs({ ...newUserInputs, projectRole: selected.optionValue })}
                                            >
                                                {["Member", "Owner"].map(option => (
                                                    <Option key={option} text={option} value={option}>
                                                        {option}
                                                    </Option>
                                                ))}
                                            </Dropdown>
                                        </div>
                                    </div>
                                </DialogContent>
                                <DialogActions style={{ justifyContent: "space-between" }}>
                                    <DialogTrigger disableButtonEnhancement>
                                        <Button appearance="secondary">Close</Button>
                                    </DialogTrigger>
                                    {loading && <Spinner label="Loading..." labelPosition="below" size="extra-small" />}
                                    <Button appearance="primary" type="submit" disabled={loading}>
                                        Create User
                                    </Button>
                                </DialogActions>
                            </form>
                        </DialogBody>
                    </DialogSurface>
                </Dialog>

                {selectedUser && selectedProject && (
                    <Dialog open={openSettingsDialog} onOpenChange={(_, data) => setOpenSettingsDialog(data.open)}>
                        <DialogSurface style={{ maxWidth: "400px" }}>
                            <DialogBody
                                style={{
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "center",
                                    flexDirection: "column"
                                }}
                            >
                                <DialogTitle>
                                    Edit {selectedUser.firstName} {selectedUser.lastName} profile
                                </DialogTitle>
                                <DialogContent>
                                    <div className={`${styles.inputColumn} ${styles.edit}`}>
                                        <div className={styles.inputGroup}>
                                            <Label>Project Role</Label>
                                            <Dropdown
                                                name="projectRole"
                                                defaultValue="Member"
                                                defaultSelectedOptions={["Member"]}
                                                onOptionSelect={(_, selected) => setNewUserRole(selected.optionValue || "")}
                                            >
                                                {["Member", "Owner"].map(option => (
                                                    <Option key={option} text={option} value={option}>
                                                        {option}
                                                    </Option>
                                                ))}
                                            </Dropdown>
                                            <Button
                                                appearance="primary"
                                                onClick={() => handleChangeUserRole(selectedProject.projectID, selectedUser, newUserRole)}
                                                disabledFocusable={selectedUser.projectRole === newUserRole}
                                            >
                                                Change Role
                                            </Button>
                                            {loading && <Spinner label="Loading..." labelPosition="below" size="extra-small" />}
                                        </div>
                                    </div>
                                </DialogContent>
                                <DialogActions style={{ justifyContent: "space-between" }}>
                                    <DialogTrigger disableButtonEnhancement>
                                        <Button appearance="secondary">Close</Button>
                                    </DialogTrigger>
                                    <Button
                                        appearance="primary"
                                        color="red"
                                        style={{ backgroundColor: "#f00" }}
                                        onClick={() => handleRemoveUser(selectedProject.projectID, selectedUser)}
                                        disabled={loading}
                                    >
                                        Remove User from project
                                    </Button>
                                </DialogActions>
                            </DialogBody>
                        </DialogSurface>
                    </Dialog>
                )}
            </div>
        </div>
    );
}
