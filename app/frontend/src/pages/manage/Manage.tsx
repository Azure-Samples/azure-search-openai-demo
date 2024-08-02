import { useState, useEffect, FormEventHandler, FormEvent } from "react";
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
    TableCellLayout
} from "@fluentui/react-components";

import { Premium20Regular } from "@fluentui/react-icons";
import styles from "./Manage.module.css";
import axios from "axios";

interface User {
    uuid: string;
    emailAddress: string;
    firstName: string;
    lastName: string;
    initialPasswordChanged: boolean;
    projectName?: string;
    projectId?: string;
    projectRole?: string;
}

interface Project {
    projectId: string;
    projectName: string;
    users: User[];
}

const testUser0 = {
    uuid: "admin123",
    emailAddress: "admin@sample.com",
    firstName: "Admin",
    lastName: "User",
    initialPasswordChanged: true,
    projectRole: "Admin"
};
const testUser1: User = {
    uuid: "abcd123",
    emailAddress: "abcd123@sample.com",
    firstName: "John",
    lastName: "Doe",
    initialPasswordChanged: false,
    projectName: "Test Project 1",
    projectId: "1",
    projectRole: "Owner"
};
const testUser2: User = {
    uuid: "efgh456",
    emailAddress: "efgh456@sample.com",
    firstName: "Jane",
    lastName: "Smith",
    initialPasswordChanged: true,
    projectName: "Test Project 1",
    projectId: "1",
    projectRole: "Member"
};
const testUser3: User = {
    uuid: "ijkl789",
    emailAddress: "ijkl789@sample.com",
    firstName: "Alice",
    lastName: "Johnson",
    initialPasswordChanged: true,
    projectName: "Test Project 1",
    projectId: "1",
    projectRole: "Member"
};
const testUser4: User = {
    uuid: "mnop123",
    emailAddress: "mnop123@sample.com",
    firstName: "Bob",
    lastName: "Brown",
    initialPasswordChanged: false,
    projectName: "Test Project 2",
    projectId: "2",
    projectRole: "Owner"
};
const testUser5: User = {
    uuid: "qrst456",
    emailAddress: "qrst456@sample.com",
    firstName: "Sarah",
    lastName: "Davis",
    initialPasswordChanged: true,
    projectName: "Test Project 2",
    projectId: "2",
    projectRole: "Member"
};
const testUser6: User = {
    uuid: "uvwx789",
    emailAddress: "uvwx789@sample.com",
    firstName: "Tom",
    lastName: "Wilson",
    initialPasswordChanged: true,
    projectName: "Test Project 2",
    projectId: "2",
    projectRole: "Member"
};
const testUser7: User = {
    uuid: "yzab123",
    emailAddress: "yzab123@sample.com",
    firstName: "Emily",
    lastName: "Taylor",
    initialPasswordChanged: false,
    projectName: "Test Project 3",
    projectId: "3",
    projectRole: "Owner"
};
const testUser8: User = {
    uuid: "cdef456",
    emailAddress: "cdef456@sample.com",
    firstName: "Michael",
    lastName: "Anderson",
    initialPasswordChanged: false,
    projectName: "Test Project 3",
    projectId: "3",
    projectRole: "Member"
};
const testUser9: User = {
    uuid: "ghij789",
    emailAddress: "ghij789@sample.com",
    firstName: "Olivia",
    lastName: "Clark",
    initialPasswordChanged: true,
    projectName: "Test Project 3",
    projectId: "3",
    projectRole: "Member"
};

const testProject1 = {
    projectId: "1",
    projectName: "Test Project 1",
    users: [testUser1, testUser2, testUser3]
};
const testProject2 = {
    projectId: "2",
    projectName: "Test Project 2",
    users: [testUser4, testUser5, testUser6]
};
const testProject3 = {
    projectId: "3",
    projectName: "Test Project 3",
    users: [testUser7, testUser8, testUser9]
};

export default function Manage(): JSX.Element {
    const [currentUser, setCurrentUser] = useState<User | null>(null);
    const [projects, setProjects] = useState<Project[]>([testProject1, testProject2, testProject3]);
    const [newUserInputs, setNewUserInputs] = useState<User>({
        uuid: "",
        emailAddress: "",
        firstName: "",
        lastName: "",
        initialPasswordChanged: false,
        projectName: "",
        projectId: "",
        projectRole: "Member"
    });
    const [newProjectInputs, setNewProjectInputs] = useState<Project>({
        projectId: "",
        projectName: "",
        users: []
    });
    const [openCreateUser, setOpenCreateUser] = useState(false);
    const [openCreateProject, setOpenCreateProject] = useState(false);

    // const createColumns = () => {
    //     if (currentUser?.projectRole === "Admin") {
    //         const projectlist = projects;
    //     } else if (currentUser?.projectRole === "Owner") {
    //         const projectlist = projects.filter(project => project.users.some(user => user.uuid === currentUser.uuid));
    //     } else if (currentUser?.projectRole === "Member") {
    //         const projectlist = projects.filter(project => project.users.some(user => user.uuid === currentUser.uuid));
    //     }
    // };

    const columns = [
        { columnKey: "firstName", name: "First Name" },
        { columnKey: "lastName", name: "Last Name" },
        { columnKey: "emailAddress", name: "User Email" },
        { columnKey: "projectRole", name: "Project Role" },
        { columnKey: "initialPasswordChanged", name: "Initial Password Changed" }
    ];

    const baseURL = 'https://us-central1-projectpalai-83a5f.cloudfunctions.net/'


    const showProject = () => {
        if (currentUser?.projectRole === "Admin") {
            return (
                <>
                    <h2>Projects (viewing as {currentUser?.projectRole})</h2>
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
                                            {project.users.map((user, index) => (
                                                <TableRow key={index}>
                                                    <TableCellLayout media={user.projectRole === "Owner" ? <Premium20Regular /> : {}}>
                                                        <TableCell>{user.firstName}</TableCell>
                                                    </TableCellLayout>
                                                    <TableCell>{user.lastName}</TableCell>
                                                    <TableCell>{user.emailAddress}</TableCell>
                                                    <TableCell>{user.projectRole}</TableCell>
                                                    <TableCell>{user.initialPasswordChanged ? "Yes" : "No"}</TableCell>
                                                </TableRow>
                                            ))}
                                        </TableBody>
                                    </Table>
                                    <Button onClick={() => setOpenCreateUser(true)} style={{ marginTop: "10px" }}>
                                        Create new user
                                    </Button>
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
                                                <form onSubmit={createUser} style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
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
                                                                <Input
                                                                    name="emailAddress"
                                                                    placeholder="Email Address"
                                                                    onChange={handleUserInputChange}
                                                                    required
                                                                />
                                                            </div>
                                                            <div className={styles.inputGroup}>
                                                                <Label>Project Role</Label>
                                                                <Dropdown
                                                                    name="projectRole"
                                                                    defaultValue="Member"
                                                                    defaultSelectedOptions={["Member"]}
                                                                    onOptionSelect={(_, selected) =>
                                                                        setNewUserInputs({ ...newUserInputs, projectRole: selected.optionValue })
                                                                    }
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
                                                        <Button
                                                            appearance="primary"
                                                            type="submit"
                                                            onClick={() =>
                                                                setNewUserInputs({
                                                                    ...newUserInputs,
                                                                    projectName: project.projectName,
                                                                    projectId: project.projectId
                                                                })
                                                            }
                                                        >
                                                            Create User
                                                        </Button>
                                                    </DialogActions>
                                                </form>
                                            </DialogBody>
                                        </DialogSurface>
                                    </Dialog>
                                </AccordionPanel>
                            </AccordionItem>
                        ))}
                        <Button onClick={() => setOpenCreateProject(true)}>Create new Project</Button>

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
                                    <form onSubmit={createProject} style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
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
                    </Accordion>
                </>
            );
        } else if (currentUser?.projectRole === "Owner") {
            return (
                <>
                    <h2>Projects (viewing as {currentUser?.projectRole})</h2>
                    {projects
                        .filter(project => project.users.some(user => user.uuid === currentUser.uuid))
                        .map((project, index) => (
                            <div key={index}>
                                <Table arial-label="Default table" style={{ minWidth: "510px" }}>
                                    <TableHeader>
                                        <h2>{project.projectName}</h2>
                                        <TableRow>
                                            {columns.map(column => (
                                                <TableHeaderCell key={column.columnKey}>
                                                    <h3>{column.name}</h3>
                                                </TableHeaderCell>
                                            ))}
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {project.users.map((user, index) => (
                                            <TableRow key={index}>
                                                <TableCell>{user.emailAddress}</TableCell>
                                                <TableCell>{user.firstName}</TableCell>
                                                <TableCell>{user.lastName}</TableCell>
                                                <TableCell>{user.projectRole}</TableCell>
                                                <TableCell>{user.initialPasswordChanged ? "Yes" : "No"}</TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                                <Button onClick={() => setOpenCreateUser(true)} style={{ marginTop: "10px" }}>
                                    Create new user
                                </Button>
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
                                            <form onSubmit={createUser} style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
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
                                                            <Input name="emailAddress" placeholder="Email Address" onChange={handleUserInputChange} required />
                                                        </div>
                                                        <div className={styles.inputGroup}>
                                                            <Label>Project Role</Label>
                                                            <Dropdown
                                                                name="projectRole"
                                                                defaultValue="Member"
                                                                defaultSelectedOptions={["Member"]}
                                                                onOptionSelect={(_, selected) =>
                                                                    setNewUserInputs({ ...newUserInputs, projectRole: selected.optionValue })
                                                                }
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
                                                    <Button
                                                        appearance="primary"
                                                        type="submit"
                                                        onClick={() =>
                                                            setNewUserInputs({
                                                                ...newUserInputs,
                                                                projectName: project.projectName,
                                                                projectId: project.projectId
                                                            })
                                                        }
                                                    >
                                                        Create User
                                                    </Button>
                                                </DialogActions>
                                            </form>
                                        </DialogBody>
                                    </DialogSurface>
                                </Dialog>
                            </div>
                        ))}
                </>
            );
        } else if (currentUser?.projectRole === "Member") {
            return (
                <>
                    <h2>Projects (viewing as {currentUser?.projectRole})</h2>
                    {projects
                        .filter(project => project.users.some(user => user.uuid === currentUser.uuid))
                        .map((project, index) => (
                            <Table arial-label="Default table" style={{ minWidth: "510px" }} key={index}>
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
                                    {project.users.map((user, index) => (
                                        <TableRow key={index}>
                                            <TableCell>{user.emailAddress}</TableCell>
                                            <TableCell>{user.firstName}</TableCell>
                                            <TableCell>{user.lastName}</TableCell>
                                            <TableCell>{user.projectRole}</TableCell>
                                            <TableCell>{user.initialPasswordChanged ? "Yes" : "No"}</TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        ))}
                </>
            );
        }
    };

    const handleUserInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        const { name, value } = event.target;
        setNewUserInputs({ ...newUserInputs, [name]: value });
    };

    const handleProjectInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        const { name, value } = event.target;
        setNewProjectInputs({ ...newProjectInputs, [name]: value });
    };


const createUserDB = (user:any) => {

    axios.post(baseURL + 'createNewAccount', 
       user
    ).then((response) => {

    });
  }

    const createUser = (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        const uuid = Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
        const emailAddress = newUserInputs?.emailAddress as string;
        const firstName = newUserInputs?.firstName as string;
        const lastName = newUserInputs?.lastName as string;
        const projectRole = newUserInputs?.projectRole as string;
        const projectId = newUserInputs?.projectId as string;
        const projectName = newUserInputs?.projectName as string;

        const newUser: User = {
            uuid: uuid,
            emailAddress: emailAddress,
            firstName: firstName,
            lastName: lastName,
            initialPasswordChanged: false,
            projectName: projectName,
            projectId: projectId,
            projectRole: projectRole
        };

        createUserDB(newUser)

        projects.forEach(project => {
            if (project.projectId === projectId) {
                project.users.push(newUser);
            }
        });

        setNewUserInputs({
            uuid: "",
            emailAddress: "",
            firstName: "",
            lastName: "",
            initialPasswordChanged: false,
            projectName: "",
            projectId: "",
            projectRole: ""
        });
        setOpenCreateUser(false);
    };

    const createProject = (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        const projectId = Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
        const projectName = newProjectInputs?.projectName as string;
        const newProject: Project = {
            projectId: projectId,
            projectName: projectName,
            users: []
        };
        projects.push(newProject);
        setNewProjectInputs({
            projectId: "",
            projectName: "",
            users: []
        });
        setOpenCreateProject(false);
    };

    useEffect(() => {
        setCurrentUser(testUser0);
        if (currentUser?.projectRole === "Admin") {
            setProjects([testProject1, testProject2, testProject3]);
        } else if (currentUser?.projectRole === "Owner") {
            setProjects(projects.filter(project => project.users.some(user => user.uuid === currentUser.uuid)));
        } else if (currentUser?.projectRole === "Member") {
            setProjects(projects.filter(project => project.users.some(user => user.uuid === currentUser.uuid)));
        }
    }, []);

    return (
        <div className={styles.container}>
            <h1>Manage</h1>
            <div className={styles.projects}>{showProject()}</div>
        </div>
    );
}
