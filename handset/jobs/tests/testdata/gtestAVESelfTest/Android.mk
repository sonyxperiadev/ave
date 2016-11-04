LOCAL_PATH := $(call my-dir)
include $(CLEAR_VARS)

LOCAL_SRC_FILES := gtestAVESelfTest.cpp
LOCAL_MODULE := gtestAVESelfTest
LOCAL_MODULE_TAGS := eng
LOCAL_SHARED_LIBRARIES := libstlport
LOCAL_STATIC_LIBRARIES := libgtest libgtest_main
LOCAL_MODULE_PATH := $(TARGET_OUT_OPTIONAL_EXECUTABLES)
LOCAL_C_INCLUDES := \
    $(TOPDIR)external/gtest/include \
    $(TOPDIR)external/stlport/stlport \
    $(TOPDIR)bionic/
    $(LOCAL_PATH)\
LOCAL_PRELINK_MODULE := false
include $(BUILD_EXECUTABLE)
