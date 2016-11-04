#include <gtest/gtest.h>
#include <iostream>

int add(int a, int b) {
	return a+b;
}

int multiply(int a, int b) {
	return a*b;
}

TEST(AVESelfTest, AddTestPass) {
  EXPECT_EQ(10, add(5,5));
}

TEST(AVESelfTest, AddTestFail) {
  // this test should fail
  EXPECT_EQ(10, add(4,5));
}

TEST(AVESelfTest, SleepTestPass) {
  ::sleep(5);
  EXPECT_EQ(12, add(7,5));
}

TEST(AVESelfTest, MultiplyTestPass) {
  EXPECT_EQ(25, multiply(5,5));
}

TEST(AVESelfTest, MultiplyTestFail) {
  // this test should fail
  EXPECT_EQ(10, multiply(5,5));
}

int main(int argc, char **argv) {
  testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}
