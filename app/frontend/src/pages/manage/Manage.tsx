import React, { useState, useEffect, FormEventHandler, FormEvent } from "react";
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
    Spinner
} from "@fluentui/react-components";

import { Premium20Regular, Edit20Regular, Eye20Regular, EyeOff20Regular } from "@fluentui/react-icons";
import styles from "./Manage.module.css";
import { auth } from "../..";
import axios from "axios";
import { onAuthStateChanged } from "firebase/auth";
import { v4 as uuidv4 } from "uuid";

interface User {
    uuid: string;
    emailAddress: string;
    firstName: string;
    lastName: string;
    password?: string;
    initialPasswordChanged: boolean;
    projectName?: string;
    projectID?: string;
    projectRole?: string;
}
interface NewUser {
    uuid: string;
    emailAddress: string;
    projectRole: string;
    projectID: string;
}

interface Project {
    projectID: string;
    projectName: string;
    users: User[];
    dateCreated: string;
}
interface NewProject {
    projectID: string;
    projectName: string;
    dateCreated: string;
}

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

    const columns = [
        { columnKey: "firstName", name: "First Name" },
        { columnKey: "lastName", name: "Last Name" },
        { columnKey: "emailAddress", name: "User Email" },
        { columnKey: "projectRole", name: "Project Role" },
        { columnKey: "initialPasswordChanged", name: "Initial Password Changed" }
    ];

    const baseURL = "https://us-central1-projectpalai-83a5f.cloudfunctions.net/";
    const baseURL2 = "http://127.0.0.1:5001/projectpalai-83a5f/us-central1/";

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
        axios.post(baseURL + "createNewAccount", user).then(response => {});
    };

    const handleAddUserToProject = (projectID: string, user: NewUser) => {
        return axios.post(baseURL + "addNewUserToProject", { projectID, user });
    };

    const handleCreateUser = (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
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

        handleCreateUserDB(newUser);
        // axios.post(baseURL2 + "createNewAccount", newUser).then(response => {
        //     axios.post(baseURL2 + "addNewUserToProject", { projectID, newUserProject }).then(response => {});
        // })
        handleAddUserToProject(projectID, newUserProject).then(response => {
            newUser.projectRole = projectRole;

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

            setOpenCreateUser(false);
        });
    };

    const handleCreateProject = (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
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
            setOpenCreateProject(false);
        });
    };

    const handleRemoveUser = (projectID: string, user: User) => {
        console.log(projectID, user.uuid, user.projectRole);
        axios.post(baseURL + "removeUserFromProject", { projectID: projectID, uuid: user.uuid, projectRole: user.projectRole }).then(response => {
            console.log("User removed from project");
            projects.forEach(project => {
                if (project.users.some(user => user.uuid === user.uuid) && projectID === project.projectID) {
                    project.users = project.users.filter(projectUser => projectUser.uuid !== user.uuid);
                }
            });
            setOpenSettingsDialog(false);
        });
    };

    const handleChangeUserRole = (projectID: string, user: User, newRole: string) => {
        console.log(user, newRole);
        if (user.projectRole === newRole) {
            return;
        }
        axios.post(baseURL + "changeUserRole", { projectID: projectID, user: user, newRole: newRole }).then(response => {
            console.log("User role changed");
            projects.forEach(project => {
                if (project.projectID === user.projectID && project.users) {
                    project.users.forEach(projectUser => {
                        if (projectUser.uuid === user.uuid) {
                            projectUser.projectRole = newRole;
                        }
                    });
                }
            });
            setNewUserRole("Member");
            setOpenSettingsDialog(false);
        });
    };

    useEffect(() => {
        const unsubscribe = onAuthStateChanged(auth, user => {
            if (user) {
                axios.get(baseURL + "getAccountDetails", { params: { clientID: user.uid } }).then(response => {
                    console.log(response.data);
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
                                <Table arial-label="Default table" style={{ minWidth: "510px" }}>
                                    <TableHeader>
                                        <TableRow>
                                            {columns.map(column => (
                                                <TableHeaderCell key={column.columnKey}>
                                                    <h3>{column.name}</h3>
                                                </TableHeaderCell>
                                            ))}
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {project.users &&
                                            project.users.map((user, index) => (
                                                <React.Fragment key={index}>
                                                    <TableRow>
                                                        <TableCell>
                                                            <TableCellLayout media={user.projectRole === "Owner" ? <Premium20Regular /> : ""}>
                                                                {user.firstName}
                                                            </TableCellLayout>
                                                        </TableCell>
                                                        <TableCell>{user.lastName}</TableCell>
                                                        <TableCell>{user.emailAddress}</TableCell>
                                                        <TableCell>{user.projectRole}</TableCell>
                                                        <TableCell>{user.initialPasswordChanged ? "Yes" : "No"}</TableCell>
                                                        {currentUser &&
                                                            (currentUser.projectRole === "Admin" ||
                                                                currentUser.projectRole === "Owner" ||
                                                                (project.users &&
                                                                    project.users.some(
                                                                        user => user.uuid === currentUser.uuid && user.projectRole === "Owner"
                                                                    ))) && (
                                                                <TableCell>
                                                                    <Edit20Regular
                                                                        style={{ cursor: "pointer" }}
                                                                        onClick={() => handleEditClick(user, project)}
                                                                    />
                                                                </TableCell>
                                                            )}
                                                    </TableRow>
                                                </React.Fragment>
                                            ))}
                                    </TableBody>
                                </Table>
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
                                    <div className={styles.inputColumn}>
                                        <div className={styles.inputGroup}>
                                            <Label>Project Name</Label>
                                            <Input name="projectName" placeholder="Project Name" onChange={handleProjectInputChange} required />
                                        </div>
                                    </div>
                                </DialogContent>
                                <DialogActions style={{ justifyContent: "space-between" }}>
                                    <DialogTrigger disableButtonEnhancement>
                                        <Button appearance="secondary">Close</Button>
                                    </DialogTrigger>
                                    <Button appearance="primary" type="submit">
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
                                            <Input name="firstName" placeholder="First Name" onChange={handleUserInputChange} required />
                                        </div>
                                        <div className={styles.inputGroup}>
                                            <Label>Last Name</Label>
                                            <Input name="lastName" placeholder="Last Name" onChange={handleUserInputChange} required />
                                        </div>
                                        <div className={styles.inputGroup}>
                                            <Label>Email Address</Label>
                                            <Input name="emailAddress" placeholder="Email Address" onChange={handleUserInputChange} required type="email" />
                                        </div>
                                        <div className={styles.inputGroup}>
                                            <Label>Password</Label>
                                            <Input
                                                id="passwordInput"
                                                name="password"
                                                placeholder="Password"
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
                                    <Button appearance="primary" type="submit">
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
