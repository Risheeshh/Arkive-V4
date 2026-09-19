from app.services.user_service import get_user_by_email, create_user, authenticate_user
from app.services.bookmark_service import (
    get_bookmark,
    get_bookmarks,
    create_bookmark,
    update_bookmark,
    delete_bookmark,
    add_tags_to_bookmark,
    remove_tag_from_bookmark,
)
