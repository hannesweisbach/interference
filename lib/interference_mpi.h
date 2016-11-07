#pragma once

#ifdef __cplusplus
extern "C" {
#endif /* __cplusplus */

  int get_ranks();
  int get_my_rank();
  void gather_longs(long my_long, long* longs);
  void gather_names(const char *my_name, char *names, unsigned name_len);
  void barrier();

#ifdef __cplusplus
}
#endif /* __cplusplus */
