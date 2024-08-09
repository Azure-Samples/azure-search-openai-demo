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
