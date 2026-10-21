"""Run expanded STS models only; candidate binaries are never executed."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from extractor.runtime_trace import start_runtime_trace

start_runtime_trace()
from extractor.corpus_runner import CorpusRunner


def expected(inputs):
    case,a,b,x,initial = inputs
    words = [initial ^ i for i in range(8)]
    memory = [(word >> (8*j)) & 255 for word in words for j in range(4)]
    if case == 0:
        for j in range(4):
            memory[4*a+j] = (x >> (8*j)) & 255
        result = x if a == b else words[b]
    elif case == 1:
        memory[a:a+2] = [x & 255, (x >> 8) & 255]
        result = x & 65535
    else:
        result = x // initial + x % initial if initial else 0
    return result,memory


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', action='append', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    records = []
    for path in args.model:
        model = json.loads(Path(path).read_text())
        assert model['status'] == 'PASS'
        runner = CorpusRunner(model['fresh_model'])
        assert runner.state_coverage == 'architecture'
        case = ('alias','overlap','division').index(model['root'])
        count = 0
        for x in (0,1,0x80000000,0xffffffff):
            for a,b in ((0,0),(0,7),(7,7),(7,0)):
                for initial in (0,1,3,0xffffffff):
                    inputs = (case,a,b,x,initial)
                    actual = runner.run(inputs)
                    result,memory = expected(inputs)
                    assert actual['status'] == 'RETURN', (path,inputs,actual)
                    assert (actual['result'],actual['memory']) == (result,memory), (path,inputs,actual)
                    count += 1
        records.append({'root':model['root'],'optimization':model['optimization'],
                        'elf_sha256':model['elf_sha256'],'model_cases':count,'status':'PASS'})
    Path(args.output).write_text(json.dumps({'status':'PASS','records':records,
                                             'native_executed':False},indent=2)+'\n')


if __name__ == '__main__':
    main()
