#  Copyright 2021, Verizon Media
#  Licensed under the terms of the ${MY_OSI} license. See the LICENSE file in the project root for terms

#  Copyright 2021, Verizon Media
#  Licensed under the terms of the ${MY_OSI} license. See the LICENSE file in the project root for terms
import requests
from pydantic import validate_arguments
from requests import Response, Session

from vzmi.ychaos.core.verification.data import (
    VerificationData,
    VerificationStateData,
)
from vzmi.ychaos.core.verification.plugins.BaseVerificationPlugin import (
    BaseVerificationPlugin,
)
from vzmi.ychaos.testplan.verification import HTTPRequestVerification


class HTTPRequestVerificationPlugin(BaseVerificationPlugin):

    __verification_type__ = "http_request"

    @validate_arguments
    def __init__(
        self,
        config: HTTPRequestVerification,
        state_data: VerificationData = VerificationData.parse_obj(dict()),
    ):
        super(HTTPRequestVerificationPlugin, self).__init__(config, state_data)
        self._session = self._build_session()

    def _build_session(self):
        session = Session()

        session.params = self.config.params
        session.headers = self.config.headers

        if not self.config.verify:
            # Disable Insecure Request Warning if verify=False (User knows what he is doing)
            from requests.packages.urllib3.exceptions import (
                InsecureRequestWarning,
            )

            requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

        session.verify = self.config.verify

        if self.config.basic_auth:
            session.auth = (
                self.config.basic_auth[0],
                self.config.basic_auth[1].get_secret_value(),
            )

        if self.config.bearer_token:
            session.headers["Authorization"] = (
                "Bearer " + self.config.bearer_token.get_secret_value()
            )

        session.cert = self.config.cert

        return session

    def run_verification(self) -> VerificationStateData:
        _rc = 0
        _data = list()

        def get_counter_data(r: Response):
            return dict(
                url=r.url,
                status_code=r.status_code,
                latency=r.elapsed.microseconds / 1000,
            )

        for _ in range(self.config.count):
            counter_data = list()

            for url in self.config.urls:
                response = self._session.request(self.config.method, url=str(url))
                if (
                    response.status_code not in self.config.status_codes
                    or (response.elapsed.microseconds / 1000) > self.config.latency
                ):
                    _rc = 1
                    counter_data.append(get_counter_data(response))
            _data.append(counter_data)

        return VerificationStateData(
            rc=_rc, type=self.__verification_type__, data=_data
        )
