import datetime
import asyncio
import logging
import math

from dateutil.relativedelta import relativedelta
from .util import string_to_padded_hex, string_to_hex, hex_to_ascii, hex_to_double
from .exceptions import AuthenticationError


_LOGGER = logging.getLogger(__name__)

class API:

    energy_req_type_3_format = "785634129001000248000000{address}00000000020000000200000001000000{months_str}00{months_str}00312c322c332c342c350000000000000000000000"

    def __init__(self, ip, port, auth1, auth2):
        self.ip = ip
        self.port = port
        self.auth1 = auth1
        self.auth2 = auth2

        self.address = self.auth1[24:48]
        _LOGGER.debug(f"주소 : {self.address}")
        _LOGGER.debug(f"주소2 : {self.auth1[32:48]}")


    async def get_energy_data(self):
        
        try:
            energy_response_dict = {}

            _LOGGER.debug(f"========== 소켓 통신 시작 ==========")
            _LOGGER.debug(f"ip : {self.ip}")
            _LOGGER.debug(f"port : {self.port}")
            reader, writer = await asyncio.open_connection(self.ip, self.port)

            # 인증 정보 전송
            writer.write(bytes.fromhex(self.auth1))
            await writer.drain()

            # 인증 응답 대기 (10초 timeout 설정)
            try:
                auth_response = (await asyncio.wait_for(reader.read(1024), timeout=10.0)).hex()
                _LOGGER.debug(f'인증 응답 패킷: {auth_response}')
            except asyncio.TimeoutError:
                _LOGGER.error("인증 timeout")
                return {}
                                        
            if auth_response[16:24] == "4c030000" and auth_response[24:48]==self.address:
                _LOGGER.debug("인증 성공")

                # 인증 정보2 전송
                writer.write(bytes.fromhex(self.auth2))
                await writer.drain()

                # 인증 응답 대기 (10초 timeout 설정)
                try:
                    auth_response = (await asyncio.wait_for(reader.read(1024), timeout=10.0)).hex()
                    _LOGGER.debug(f'인증 응답 패킷: {auth_response}')
                except asyncio.TimeoutError:
                    _LOGGER.error("인증 timeout")
                    return {}

                if auth_response[16:24] == "04000000" and auth_response[24:48]==self.address:
                    _LOGGER.debug("인증 성공")

                    # 에너지 조회 패킷 전송
                    energy_req_data = ""
                    ########## 에너지 요청 데이터 가공 ##########
                    # 이번달
                    months_str = datetime.datetime.now().strftime("%Y-%m-00 00:00:00")
                    _LOGGER.debug(f'요청 날짜: {months_str}')
                    energy_req_data = self.energy_req_type_3_format.format(address=self.address, months_str=string_to_hex(months_str))

                    _LOGGER.debug(f"에너지 정보 요청 패킷 : {energy_req_data}")
                    writer.write(bytes.fromhex(energy_req_data))
                    await writer.drain()

                    # 조회 응답 대기 (10초 timeout 설정)
                    try:
                        gnergy_response = (await asyncio.wait_for(reader.read(1024), timeout=10.0)).hex()
                        _LOGGER.debug(f'에너지 정보 수신 패킷: {gnergy_response}')

                        # 에너지 정보 수신 패킷 검증
                        if len(gnergy_response) < 500:  # 정상적인 응답 패킷 길이보다 짧은 경우
                            _LOGGER.error(f"비정상 응답 데이터 수신. 응답 길이: {len(gnergy_response)}")
                            return None

                        # 전기
                        start_idx = 184
                        response_ym = hex_to_ascii(gnergy_response[start_idx + 8 : start_idx + 22])
                        _LOGGER.debug(f"이번달 조회 년월 : {response_ym}, raw_data   : {gnergy_response[start_idx + 8 : start_idx + 22]}")
                        usage = hex_to_double(gnergy_response[start_idx + 48 : start_idx + 64])
                        _LOGGER.debug(f"이번달 전기 사용량 : {usage}, raw_data : {gnergy_response[start_idx + 48 : start_idx + 64]}")
                        energy_response_dict["this_month"] = response_ym
                        energy_response_dict["electricity_usage_this_month"] = usage

                        # 수도
                        start_idx = 272
                        usage = hex_to_double(gnergy_response[start_idx + 48 : start_idx + 64])
                        _LOGGER.debug(f"이번달 수도 사용량 : {usage}, raw_data : {gnergy_response[start_idx + 48 : start_idx + 64]}")
                        energy_response_dict["water_usage_this_month"] = usage

                        # 온수
                        start_idx = 360
                        usage = hex_to_double(gnergy_response[start_idx + 48 : start_idx + 64])
                        _LOGGER.debug(f"이번달 온수 사용량 : {usage}, raw_data : {gnergy_response[start_idx + 48 : start_idx + 64]}")
                        energy_response_dict["hot_water_usage_this_month"] = usage

                        # 가스
                        start_idx = 448
                        usage = hex_to_double(gnergy_response[start_idx + 48 : start_idx + 64])
                        _LOGGER.debug(f"이번달 가스 사용량 : {usage}, raw_data : {gnergy_response[start_idx + 48 : start_idx + 64]}")
                        energy_response_dict["gas_usage_this_month"] = usage

                        # 난방
                        start_idx = 536
                        usage = hex_to_double(gnergy_response[start_idx + 48 : start_idx + 64])
                        _LOGGER.debug(f"이번달 난방 사용량 : {usage}, raw_data : {gnergy_response[start_idx + 48 : start_idx + 64]}")
                        energy_response_dict["heating_usage_this_month"] = usage



                    except asyncio.TimeoutError:
                        _LOGGER.error("응답시간이 초과되었습니다.")
                        return {}
                else:
                    _LOGGER.error(f"인증정보가 올바르지 않습니다.")

            else :
                 _LOGGER.error(f"인증정보가 올바르지 않습니다.")

            _LOGGER.debug(f"========== 소켓 통신 종료 ==========")
            return energy_response_dict

        except Exception as e:
            _LOGGER.error(f"소켓 통신 오류: {e}")
        finally:
            # 연결 종료
            writer.close()
            await writer.wait_closed()

