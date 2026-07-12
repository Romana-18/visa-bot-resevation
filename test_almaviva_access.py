# import requests
# from utility import rotate_proxy
# def test_rotate_proxy():
#     proxy = rotate_proxy()
#     proxies = proxy if isinstance(proxy, dict) else {}
#     try:
#         response = requests.get("https://egy.almaviva-visa.it/", proxies=proxies, timeout=10)
#         print(f"Proxy: {proxies}")
#         print(f"Status code: {response.status_code}")
#         if response.status_code == 200:
#             print("Website is accessible through proxy.")
#         else:
#             print("Website returned a non-200 status code.")
#     except Exception as e:
#         print(f"Error accessing the website through proxy: {e}")

# # Call this function to test
# test_rotate_proxy()