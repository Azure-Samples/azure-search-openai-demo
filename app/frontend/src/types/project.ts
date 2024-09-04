interface Project {
    projectID: string;
    projectName: string;
    users: User[];
    dateCreated: string;
    projectIndex?: string;
    projectContainer?: string;
}
interface NewProject {
    projectID: string;
    projectName: string;
    dateCreated: string;
    users: User[];
    projectIndex?: string;
    projectContainer?: string;
}

interface ProjectOptions {
    projectName: string;
    projectIndex: string;
    projectContainer: string;
}
