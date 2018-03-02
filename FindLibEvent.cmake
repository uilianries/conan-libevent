
message(STATUS "${CONAN_LIB_DIRS_LIBEVENT}")

find_path(LIBEVENT_INCLUDE_DIR event.h PATHS ${CONAN_INCLUDE_DIRS_LIBEVENT})
find_library(LIBEVENT_LIB NAMES event PATHS ${CONAN_LIB_DIRS_LIBEVENT})

if (LIBEVENT_LIB AND LIBEVENT_INCLUDE_DIR)
  set(LibEvent_FOUND TRUE)
  set(LIBEVENT_LIB ${LIBEVENT_LIB})
else ()
  set(LibEvent_FOUND FALSE)
endif ()

if (LibEvent_FOUND)
  if (NOT LibEvent_FIND_QUIETLY)
    message(STATUS "Found libevent: ${LIBEVENT_LIB}")
  endif ()
else ()
  if (LibEvent_FIND_REQUIRED)
    message(FATAL_ERROR "Could NOT find libevent.")
  endif ()
  message(STATUS "libevent NOT found.")
endif ()

mark_as_advanced(
    LIBEVENT_LIB
    LIBEVENT_INCLUDE_DIR
  )
