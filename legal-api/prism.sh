#! /bin/sh

# start payment mock
PAYMENT_SPEC=https://raw.githubusercontent.com/bcgov/sbc-pay/main/docs/docs/api_contract/pay-api-1.0.0.yaml
# docker run --init --rm -p4010:4010 stoplight/prism:3 mock --errors -h 0.0.0.0 $PAYMENT_SPEC
docker run --init --rm -p4010:4010 stoplight/prism:3 mock -h 0.0.0.0 $PAYMENT_SPEC

