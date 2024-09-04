import React, { useState, useEffect, FormEvent, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { uploadFilesApi, FileUploadRequest } from "../../api";
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
import { useLogin, getToken } from "../../authConfig";
import { useMsal } from "@azure/msal-react";
import { v4 as uuidv4 } from "uuid";
import { useNavigate, useLocation } from "react-router-dom";

export default function Manage(): JSX.Element {
    const [userData, setUserData] = useState<User | null>(null);
    const [projects, setProjects] = useState<Project[]>([]);
    const [loadingPage, setLoadingPage] = useState(true);
    const [loadingSettings, setLoadingSettings] = useState(false);
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

    const currentUser = useLocation().state;
    const navigate = useNavigate();

    const [currentProject, setCurrentProject] = useState<string>("default");
    const [projectOptions, setProjectOptions] = useState<ProjectOptions[]>([]);
    const [index, setIndex] = useState<string>("gptkbindex");
    const [container, setContainer] = useState<string>("content");


    const [showFileUploaded, setShowFileUploaded] = useState(false);
    const [showFileAdded, setShowFileAdded] = useState(false);


    const baseURL = import.meta.env.VITE_FIREBASE_BASE_URL;
    const baseURL2 = "http://127.0.0.1:5001/projectpalai-83a5f/us-central1/";

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
                          userData &&
                          userData.projectRole !== "Member" &&
                          userData.uuid !== user.uuid &&
                          (user.projectRole === "Member" || (userData.projectRole === "Admin" && user.projectRole !== "Admin")) ? (
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
    };

    const handleCreateUserDB = (user: any) => {
        return axios.post(baseURL + "createNewAccount", user);
    };

    const handleAddUserToProject = (projectID: string, user: NewUser) => {
        return axios.post(baseURL + "addNewUserToProject", { projectID, user });
    };

    const handleCreateUser = (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        setLoadingSettings(true);
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
                    setLoadingSettings(false);
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
                    setLoadingSettings(false);
                    setOpenCreateUser(false);
                }
            });
        });
    };

    const handleCreateProject = (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        setLoadingSettings(true);
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
            setLoadingSettings(false);
            setOpenCreateProject(false);
        });
    };

    const handleRemoveUser = (projectID: string, user: User) => {
        setLoadingSettings(true);
        axios.post(baseURL + "removeUserFromProject", { projectID: projectID, uuid: user.uuid, projectRole: user.projectRole }).then(response => {
            console.log("User removed from project");
            projects.forEach(project => {
                if (project.users.some(user => user.uuid === user.uuid) && projectID === project.projectID) {
                    project.users = project.users.filter(projectUser => projectUser.uuid !== user.uuid);
                }
            });
            setLoadingSettings(false);
            setOpenSettingsDialog(false);
        });
    };

    const handleChangeUserRole = (projectID: string, user: User, newRole: string) => {
        setLoadingSettings(true);
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
            setLoadingSettings(false);
            setOpenSettingsDialog(false);
        });
    };

    function Dropzone({ projectID }: { projectID: string }) {
        const [filePath, setFilePath] = useState("");
        const [token, setToken] = useState<string | undefined>(undefined);
        const client = useLogin ? useMsal().instance : undefined;

        // Retrieve the token asynchronously
        useEffect(() => {
            const fetchToken = async () => {
                try {
                    console.log("Retrieving token: " + client);
                    const tokenResponse = client ? await getToken(client) : undefined;
                    setToken(tokenResponse?.accessToken);
                    console.log("Token retrieved: " + tokenResponse?.accessToken);
                } catch (error) {
                    console.error("Failed to retrieve token:", error);
                }
            };

            if (client) {
                fetchToken();
            }
        }, [client]);

        const onDrop = useCallback(
            (acceptedFiles: any) => {
                let filePaths: string[] = [];

                acceptedFiles.forEach((file: any) => {
                    filePaths.push(file.name); // Use file.name for better compatibility
                });

                setFilePath(filePaths.join(", "));

                console.log("Files added: " + filePaths.join(", "));

                // console.log("Index & Container: " + projectIndex + " " + projectContainer);

                console.log("Index & Container: " + projectID + " " + projectID);
                // Build the request object
                const request: FileUploadRequest = {
                    azureIndex: projectID,
                    azureContainer: projectID,
                    files: acceptedFiles
                };

                console.log("Request: " + JSON.stringify(request));

                setShowFileAdded(false)
                setShowFileUploaded(false)

                // Call the uploadFilesApi function to upload the files
                uploadFilesApi(request, token)
                    .then(async response => {
                        if (response.ok) {
                            console.log("Files uploaded successfully:", response);
                            setFilePath("")
                            setShowFileAdded(true)
                            // Handle success (e.g., show a success message)
                        } else {
                            // Parse and log the error message from the response body
                            const errorMessage = await response.json();
                            console.error("Error uploading files:", errorMessage);
                            // Optionally, you could display the error to the user here
                        }
                    })
                    .catch(error => {
                        console.error("Error uploading files:", error);
                        // Handle network or other errors
                    });
            },
            [token, index, container]
        );

        const { getRootProps, getInputProps } = useDropzone({ onDrop,multiple: false });

        return (
            <div {...getRootProps()} className={styles.dropzone} key={projectID}>
                <input {...getInputProps()} multiple={false}/>
                {!filePath && (
                    <>
                        <DocumentArrowUpRegular fontSize={40} style={{ color: "#409ece" }} />
                        <p style={{ margin: "0", textAlign: "center" }}>Click here or drag and drop to add your project files</p>
                    </>
                )}
                {filePath && (
                    <>
                        <DocumentArrowUpRegular fontSize={40} style={{ color: "#409ece" }} />
                        <p style={{ margin: "0", textAlign: "center" }}>{filePath}</p>
                    </>
                )}
            </div>
        );
    }

    useEffect(() => {
        if (!auth.currentUser) {
            navigate("/login");
        } else {
            const projectString = localStorage.getItem("projects");
            if (projectString) {
                const projects = JSON.parse(projectString);
                let compArray: ProjectOptions[] = [];
                projects.forEach((project: Project) => {
                    compArray.push({
                        projectName: project.projectName ?? "",
                        projectIndex: project.projectIndex ?? "",
                        projectContainer: project.projectContainer ?? ""
                    });
                });
                setProjectOptions(compArray);
                setCurrentProject(compArray[0].projectName);
                setIndex(compArray[0].projectIndex);
                setContainer(compArray[0].projectContainer);
            }
        }
    }, []);

    useEffect(() => {
        const unsubscribe = onAuthStateChanged(auth, user => {
            if (user) {
                axios.get(baseURL + "getAccountDetails", { params: { clientID: user.uid } }).then(response => {
                    const data = response.data;
                    if (data.found) {
                        setUserData(data.user);
                        axios.get(baseURL + "getProjects", { params: { clientID: user.uid } }).then(response => {
                            setProjects(response.data);
                            setLoadingPage(false);
                        });
                    }
                });
            }
        });
        return () => unsubscribe();
    }, []);

    useEffect(() => {
        if (currentUser && currentUser.userData) {
            setUserData(currentUser.userData);
        }
    });

    return (
        <div className={styles.container}>
            <h1>Manage {userData && userData.projectRole && `(Viewing as ${userData.projectRole})`}</h1>
            {loadingPage && <Spinner label="Loading..." labelPosition="below" size="large" />}
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
                                    {userData &&
                                        (userData.projectRole === "Admin" ||
                                            userData.projectRole === "Owner" ||
                                            (project.users && project.users.some(user => user.uuid === userData.uuid && user.projectRole === "Owner"))) && (
                                            <div style={{ display: "flex", flexDirection: "column" }}>
                                                <Dropzone projectID={project.projectID}/>
                                                {showFileUploaded && <span className="fileUploadText">File uploaded successfully, wait 2 minutes for it to be added to the knowledge base.<br/><strong>Do not close this tab until added</strong></span>}
                                                {showFileAdded && <span className="fileUploadText">File added to the knowledge base</span>}
                                                {/* <Button appearance="primary" style={{ marginTop: "10px" }}>
                                                    Upload file
                                                </Button> */}
                                            </div>
                                        )}
                                </div>
                                {userData &&
                                    (userData.projectRole === "Admin" ||
                                        userData.projectRole === "Owner" ||
                                        (project.users && project.users.some(user => user.uuid === userData.uuid && user.projectRole === "Owner"))) && (
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

                {userData && userData.projectRole === "Admin" && (
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
                                            {loadingSettings && <Spinner label="Loading..." labelPosition="below" size="large" />}
                                        </div>
                                    </div>
                                </DialogContent>
                                <DialogActions style={{ justifyContent: "space-between" }}>
                                    <DialogTrigger disableButtonEnhancement>
                                        <Button appearance="secondary">Close</Button>
                                    </DialogTrigger>
                                    <Button appearance="primary" type="submit" disabled={loadingSettings}>
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
                                    {loadingSettings && <Spinner label="Loading..." labelPosition="below" size="extra-small" />}
                                    <Button appearance="primary" type="submit" disabled={loadingSettings}>
                                        Create User
                                    </Button>
                                </DialogActions>
                            </form>
                        </DialogBody>
                    </DialogSurface>
                </Dialog>

                {selectedUser && selectedProject && currentUser && selectedUser.uuid !== currentUser.uuid && (
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
                                            {loadingSettings && <Spinner label="Loading..." labelPosition="below" size="extra-small" />}
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
                                        disabled={loadingSettings}
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
