from fastapi import Query

class PaginationDeps:
    """
    Common dependency for pagination.
    Usage:
        async def list_items(pagination: PaginationDeps = Depends()):
            return db_query.offset(pagination.skip).limit(pagination.limit)
    """
    def __init__(
        self,
        skip: int = Query(0, ge=0, description="Number of records to skip for pagination"),
        limit: int = Query(10, ge=1, le=100, description="Maximum number of records to return")
    ):
        self.skip = skip
        self.limit = limit
