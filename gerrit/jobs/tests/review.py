import time

from ave.gerrit import review

PROJECT  = 'semctools/ave/gerrit'
CHANGE   = '782431'
PATCHSET = '1'

def _verify_attribute(gerrit_listener, pretty, verdict, attribute):

    def _set_atribute(atribute, project, change, patchset, verdict):
        if atribute=='Verified':
            review.set_verified(project, change, patchset, verdict)
        elif atribute=='Code-Review':
            review.set_code_review(project, change, patchset, verdict)
        else:
            raise Exception('_set_attributes only accepts Verified or '
                            'Code-Review as parameter, attribute set: %s' %
                            attribute)

    #clear verdict to start with
    try:
        _set_atribute(attribute, PROJECT, CHANGE, PATCHSET, 0)
    except Exception, e:
        print('FAIL %s: unable to set %s %s : %s' % (pretty, attribute, 0, e))
        return False

    #Let the change be reported
    time.sleep(2)

    #flush the pipe
    while not gerrit_listener.pipe.empty():
        gerrit_listener.pipe.get(timeout=1)

    # set the verdict to 1
    try:
        _set_atribute(attribute, PROJECT, CHANGE, PATCHSET, verdict)
    except Exception, e:
        print('FAIL %s: unable to set %s %s : %s' %
              (pretty, attribute, verdict, e))
        return False

    # verify that the correct data was set
    attempt = 0
    while attempt < 100:
        attempt += 1
        try:
            gerrit_message = gerrit_listener.pipe.get(timeout=2)
        except Exception, e:
            print('FAIL %s: unable to read from gerrit listener pipe: %s' %
                  (pretty, e.message))
            return False

        # filter out the correct change
        if not 'change' in gerrit_message:
            continue
        if not 'number' in gerrit_message['change']:
            continue
        if gerrit_message['change']['number'] != CHANGE:
            continue
        # Verify that the correct attribute was set
        if gerrit_message['approvals'][0]['type'] != attribute:
            print('FAIL %s: failed to set attribute %s, '
                  'attribute set: %s' %
                  (pretty, attribute, gerrit_message['approvals'][0]['type']))
            return False
        if gerrit_message['approvals'][0]['value'] != str(verdict):
            print('FAIL %s: failed to set %s to %s, set value: %s'
                  % (pretty, attribute, str(verdict),
                     gerrit_message['approvals'][0]['value']))
            return False
        break

    if attempt >= 100:
        print('FAIL %s: did not receive gerrit change callback' % pretty)
        return False

    return True

# check that multiline messages with quotes in them can be escpaced correctly
def t1():
    pretty = '%s t1' % __file__
    print(pretty)

    original = 'foo\r\nb"a"r\r\n"more crap"'
    expected = '"foo\r\nb\\\"a\\\"r\r\n\\\"more crap\\\""'
    actual   =  review.quote_message(original)

    if actual != expected:
        print('FAIL %s: wrong quoting: %s' % (pretty, [t for t in actual]))
        return False

    return True

# check that message indentation works
def t2():
    pretty = '%s t2' % __file__
    print(pretty)

    original = 'foo\r\nb"a"r\r\n\r\n"more crap"'
    expected = ' foo\n b"a"r\n \n "more crap"'
    actual   =  review.indent_message(original)

    if actual != expected:
        print('FAIL %s: wrong indentation: %s' % (pretty, [a for a in actual]))
        return False

    return True

# combine quoting and indentation
def t3():
    pretty = '%s t3' % __file__
    print(pretty)

    original = 'foo\r\nb"a"r\r\n\r\n"more crap"'
    expected = '" foo\n b\\\"a\\\"r\n \n \\\"more crap\\\""'
    interrim = review.indent_message(original)
    actual   = review.quote_message(interrim)

    if actual != expected:
        print('FAIL %s: wrong indentation: %s' % (pretty, [a for a in actual]))
        return False

    return True

# testing a real gerrit  code review
def t4(gerrit_listener = None):
    pretty = '%s t4' % __file__
    verdict = 1
    print(pretty)
    return _verify_attribute(gerrit_listener, pretty, verdict, 'Verified')

def t5(gerrit_listener = None):
    pretty = '%s t5' % __file__
    verdict = -1
    print(pretty)
    return _verify_attribute(gerrit_listener, pretty, verdict, 'Code-Review')

def t6(gerrit_listener = None):
    pretty = '%s t6' % __file__
    message = 'This is a "Test Message" \nsplit on two lines'
    print(pretty)

    #flush the pipe
    while not gerrit_listener.pipe.empty():
        gerrit_listener.pipe.get(timeout=1)

    message = review.quote_message(message)
    message = review.indent_message(message)

    try:
        review.set_comment(PROJECT, CHANGE, PATCHSET, message)
    except Exception, e:
        print('FAIL %s: unable to set comment %s : %s' %
              (pretty, message, e))
        return False

    # verify that the correct data was set
    attempt = 0
    while attempt < 100:
        attempt += 1
        try:
            gerrit_message = gerrit_listener.pipe.get(timeout=2)
        except Exception, e:
            print('FAIL %s: unable to read from gerrit listener pipe: %s' %
                  (pretty, e.message))
            return False

        # filter out the correct change
        if not 'change' in gerrit_message:
            continue
        if not 'number' in gerrit_message['change']:
            continue
        if gerrit_message['change']['number'] != CHANGE:
            continue
        # Verify that the comment was set
        read_comment = gerrit_message['comment']
        exp_comment = 'Patch Set %s:\n\nThis is a "Test Message" \n ' \
                      'split on two lines' % PATCHSET
        if not exp_comment == read_comment:
            print('FAIL %s: \nError in message:\n%s. \nExpected message: \n%s' %
                  (pretty, read_comment, exp_comment))
            return False
        break

    if attempt >= 100:
        print('FAIL %s: did not receive gerrit change callback' % pretty)
        return False

    return True
