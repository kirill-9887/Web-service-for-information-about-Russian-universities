class NotUnivError(Exception):
    """The data does not apply to higher education"""
    pass


class RecordNotFoundError(Exception):
    """Record not found in database"""
    pass


class UniqueConstraintFailedError(Exception):
    """The value of some field of the record is not unique"""
    pass


class SelfCreatedIDError(Exception):
    """Attempt to insert a record into a table with a non-empty id field"""
    pass
