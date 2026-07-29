declare namespace Api {
  namespace Auth {
    interface UserInfo {
      userId: string;
      userName: string;
      email?: string;
      id?: number;
      role?: string;
      roles: string[];
      permissions: string[];
      buttons: string[];
    }
  }
}
