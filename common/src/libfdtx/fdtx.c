/*
 * Copyright (C) 2013 Sony Mobile Communications AB.
 * All rights, including trade secret rights, reserved.
 */

#include <stdio.h>

#include <sys/socket.h>
#include <sys/uio.h>
#include <errno.h>

#define MAX_FDS 8
#define MAX_IOV 31

int
fdtx_max_fds() {
    return MAX_FDS;
}

int
fdtx_recv(int sock, int *fds, unsigned n_fds, char * msg, int len)
{
    /* use the iovec part to to carry a plain string message */
    struct iovec message = {0};
    message.iov_base = msg;
    message.iov_len  = len;

    /* build the message header. file descriptors go into the payload, which is
     * an opaque array of ancillary data blobs (careful what you poke in it).
     */
    char buffer [ CMSG_SPACE(sizeof(int) * MAX_FDS) ];
    struct msghdr header  = {0}; /* free nulling */
    header.msg_iov        = &message;
    header.msg_iovlen     = 1;   /* number of iovec entries, not the chars */
    header.msg_control    = &buffer;
    header.msg_controllen = CMSG_SPACE(sizeof(int) * n_fds);

    /* build the ancillary data. the blobs must be initialized in situ inside
     * the header. i.e. one cannot first make a bunch of cmsghdr objects and
     * then add them to the header. not enough 733t I suppose...
     */
    struct cmsghdr *control;
    int i;
    control = CMSG_FIRSTHDR(&header);
    control->cmsg_len   = CMSG_LEN(sizeof(int) * n_fds);
    control->cmsg_level = SOL_SOCKET; /* payload is resources on socket level */
    control->cmsg_type  = SCM_RIGHTS; /* payload is access rights */
    for (i = 0; i < n_fds; i++) {     /* set all data to -1 to recognize */
        ((int *)CMSG_DATA(control))[i] = -1;
    }

    /* receive the message, dig out the file descriptors and be done with it */
    int tmp = recvmsg(sock, &header, 0);
    if (tmp < 0) {
        return -1;
    }
    if (tmp == 0) {
        return -2;
    }
    for (i = 0; i < n_fds; i++) {
        fds[i] = ((int *)CMSG_DATA(control))[i];
    }
    return 0;
}

int
fdtx_send(int sock, const int *fds, unsigned n_fds, const char * msg, int len)
{
    /* caller musta allocate the buffer that the iovec plain string message is
     * received into.
     */
    struct iovec message;
    message.iov_base = msg;
    message.iov_len  = len;

    /* header built exactly like before. it's a pity I don't like macros */
    char buffer [ CMSG_SPACE(sizeof(int) * MAX_FDS) ];
    struct msghdr header  = {0};
    header.msg_iov        = &message;
    header.msg_iovlen     = 1;
    header.msg_control    = &buffer;
    header.msg_controllen = CMSG_SPACE(sizeof(int) * n_fds);

    /* ancillary data built also built exactly the same, except that the data
     * is populated with the file descriptors instead of '-1' defaults
     */
    struct cmsghdr *control;
    int i;
    control = CMSG_FIRSTHDR(&header);
    control->cmsg_len   = CMSG_LEN(sizeof(int) * n_fds);
    control->cmsg_level = SOL_SOCKET;
    control->cmsg_type  = SCM_RIGHTS;
    for (i = 0; i < n_fds; i++) {
        ((int *)CMSG_DATA(control))[i] = fds[i];
    }

    if (sendmsg(sock, &header, 0) < 0) {
        return errno;
    }
    return 0;
}
