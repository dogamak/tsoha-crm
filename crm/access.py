from enum import Enum


class AccessControlGroup(Enum):
    Self = 's'
    Owner = 'O'
    Assigned = 'a'
    Group = 'g'
    Admin = 'A'
    Other = 'o'


class AccessControlList:
    def __init__(self, string=None, read=None, write=None, create=None, delete=None):
        if string is None:
            self.read = read or [ AccessControlGroup.Other ]
            self.write = write or self.read
            self.create = create or self.write
            self.delete = delete or self.create 
        else:
            self.read = []
            self.write = []
            self.create = []
            self.delete = []

            for part in string.split(','):
                acl_name, groups = part.split('=', 1)

                acl = dict(
                    w=self.write,
                    write=self.write,
                    r=self.read,
                    read=self.read,
                    c=self.create,
                    create=self.create,
                    d=self.delete,
                    delete=self.delete,
                ).get(acl_name, None)

                for group in groups:
                    try:
                        acl.append(AccessControlGroup(group))
                    except ValueError:
                        raise ValueError(f'Invalid ACL string: unknown access group identifier {group}')

            if acl is None:
                raise ValueError(f'Invalid ACL string: unknown access type identifier {acl_name}')

    def check(self, resource, user, access_type):
        from crm.models.user import UserRole

        acl = []

        if access_type == AccessType.Read:
            acl = self.read
        elif access_type == AccessType.Write:
            acl = self.write
        elif access_type == AccessType.Create:
            acl = self.create
        else:
            acl = self.delete

        print(acl, resource, user, access_type)

        return (AccessControlGroup.Other in acl) or \
            (user == resource and AccessControlGroup.Self in acl) or \
            (resource.created_by and resource.created_by == user and AccessControlGroup.Owner in acl) or \
            (user in resource.assigned_users and AccessControlGroup.Assigned in acl) or \
            (user.role == UserRole.Administrator and AccessControlGroup.Admin in acl)


class AccessType(Enum):
    Read = 'READ'
    Write = 'WRITE'
    Create = 'CREATE'
    Delete = 'DELETE'
